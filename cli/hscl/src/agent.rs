//! Bounded agent loop for AREX-style models: the model proposes tool calls, this loop validates and executes them
//! through a caller-supplied allow-listed `Tools`, feeds results back, and stops at `finish` or at the round budget.

// Temporary, see docs/superpowers/plans/2026-11-06-ai-api-updates-stress.md (Task D4): consumer `hscl agent run` follows.
#![allow(dead_code)]

use crate::toolcall::{self, Call};
use serde_json::Value;

pub const MAX_RESULT: usize = 64 * 1024;

#[derive(Debug, Clone, PartialEq)]
pub struct Msg {
    pub role: String,
    pub content: String,
}

pub trait Chat {
    fn complete(&mut self, msgs: &[Msg]) -> anyhow::Result<String>;
}

pub trait Tools {
    /// Names the model may call (besides the built-in `finish`).
    fn names(&self) -> Vec<String>;
    fn run(&mut self, name: &str, args: &Value) -> anyhow::Result<String>;
}

#[derive(Debug, Clone, PartialEq)]
pub struct Round {
    pub n: u32,
    pub tools_run: Vec<String>,
    pub refused: Option<String>,
    pub finished: bool,
}

#[derive(Debug, PartialEq)]
pub enum Outcome {
    Finished(String),
    BudgetExhausted,
}

fn cap(mut s: String) -> String {
    if s.len() > MAX_RESULT {
        let mut end = MAX_RESULT;
        while !s.is_char_boundary(end) {
            end -= 1;
        }
        s.truncate(end);
        s.push_str("\n[truncated]");
    }
    s
}

fn response(body: &str) -> Msg {
    Msg {
        role: "user".into(),
        content: format!("<tool_response>\n{body}\n</tool_response>"),
    }
}

/// Run at most `max_rounds` rounds. Each round: one model reply, parse, execute allowed calls, report via `log`.
/// A refused or malformed call is reported to the model as an error response; it never reaches `tools`.
pub fn run(
    chat: &mut dyn Chat,
    tools: &mut dyn Tools,
    goal: &str,
    max_rounds: u32,
    log: &mut dyn FnMut(&Round),
) -> anyhow::Result<Outcome> {
    let mut msgs = vec![Msg {
        role: "user".into(),
        content: goal.to_string(),
    }];
    let names = tools.names();
    for n in 1..=max_rounds {
        let reply = chat.complete(&msgs)?;
        msgs.push(Msg {
            role: "assistant".into(),
            content: reply.clone(),
        });
        let allow: Vec<&str> = names.iter().map(String::as_str).collect();
        let mut round = Round {
            n,
            tools_run: Vec::new(),
            refused: None,
            finished: false,
        };
        match toolcall::parse(&reply, &allow) {
            Err(e) => {
                let why = format!("{e:?}");
                msgs.push(response(&format!("error: {why}")));
                round.refused = Some(why);
            }
            Ok(calls) if calls.is_empty() => {
                msgs.push(response("error: no tool call; call a tool or finish"));
            }
            Ok(calls) => {
                let mut answer = None;
                for c in calls {
                    match c {
                        Call::Finish { answer: a } => {
                            answer = Some(a);
                            break;
                        }
                        Call::Tool { name, args } => {
                            let body = match tools.run(&name, &args) {
                                Ok(s) => cap(s),
                                Err(e) => format!("error: {e}"),
                            };
                            round.tools_run.push(name);
                            msgs.push(response(&body));
                        }
                    }
                }
                if let Some(a) = answer {
                    round.finished = true;
                    log(&round);
                    return Ok(Outcome::Finished(a));
                }
            }
        }
        log(&round);
    }
    Ok(Outcome::BudgetExhausted)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    struct Script(Vec<String>);
    impl Chat for Script {
        fn complete(&mut self, _m: &[Msg]) -> anyhow::Result<String> {
            if self.0.is_empty() {
                Ok("no more script".into())
            } else {
                Ok(self.0.remove(0))
            }
        }
    }
    #[derive(Default)]
    struct Rec(Vec<(String, Value)>);
    impl Tools for Rec {
        fn names(&self) -> Vec<String> {
            vec!["read_doc".into()]
        }
        fn run(&mut self, n: &str, a: &Value) -> anyhow::Result<String> {
            self.0.push((n.into(), a.clone()));
            Ok(format!("ran {n}"))
        }
    }

    fn call(name: &str) -> String {
        format!("<tool_call><function={name}><parameter=path>x</parameter></function></tool_call>")
    }

    #[test]
    fn finishes_on_finish_and_logs_each_round() {
        let mut chat = Script(vec![
            call("read_doc"),
            call("finish").replace("path", "answer"),
        ]);
        let mut tools = Rec::default();
        let mut rounds = Vec::new();
        let out = run(&mut chat, &mut tools, "goal", 5, &mut |r| {
            rounds.push(r.clone())
        })
        .unwrap();
        assert_eq!(out, Outcome::Finished("x".into()));
        assert_eq!(
            tools.0,
            vec![("read_doc".to_string(), json!({"path": "x"}))]
        );
        assert_eq!(rounds.len(), 2);
        assert_eq!(rounds[0].tools_run, vec!["read_doc"]);
        assert!(rounds[1].finished);
    }

    #[test]
    fn stops_at_the_budget_when_the_model_never_finishes() {
        let mut chat = Script(vec![]);
        let mut tools = Rec::default();
        let mut n = 0;
        let out = run(&mut chat, &mut tools, "goal", 3, &mut |_| n += 1).unwrap();
        assert_eq!(out, Outcome::BudgetExhausted);
        assert_eq!(n, 3);
    }

    #[test]
    fn a_refused_tool_is_logged_not_executed_and_the_loop_continues() {
        let mut chat = Script(vec![call("bash"), call("finish").replace("path", "answer")]);
        let mut tools = Rec::default();
        let mut rounds = Vec::new();
        let out = run(&mut chat, &mut tools, "goal", 4, &mut |r| {
            rounds.push(r.clone())
        })
        .unwrap();
        assert!(matches!(out, Outcome::Finished(_)));
        assert!(tools.0.is_empty(), "bash must never reach the tools");
        assert!(rounds[0].refused.as_deref().unwrap().contains("bash"));
    }

    #[test]
    fn tool_results_are_truncated_before_going_back_to_the_model() {
        struct Big;
        impl Tools for Big {
            fn names(&self) -> Vec<String> {
                vec!["read_doc".into()]
            }
            fn run(&mut self, _: &str, _: &Value) -> anyhow::Result<String> {
                Ok("a".repeat(MAX_RESULT * 2))
            }
        }
        struct Spy(Vec<usize>, u32);
        impl Chat for Spy {
            fn complete(&mut self, m: &[Msg]) -> anyhow::Result<String> {
                self.0.push(m.last().unwrap().content.len());
                self.1 += 1;
                Ok(if self.1 == 1 {
                    call("read_doc")
                } else {
                    call("finish").replace("path", "answer")
                })
            }
        }
        let mut chat = Spy(vec![], 0);
        run(&mut chat, &mut Big, "g", 4, &mut |_| {}).unwrap();
        assert!(chat.0[1] < MAX_RESULT + 200, "{:?}", chat.0);
    }
}
