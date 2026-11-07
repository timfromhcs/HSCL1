#![no_main]
//! Coverage-guided fuzzing of the tool-call parser on the **same file** the binary ships.
//!
//! `#[path]` includes the source instead of importing a crate: `hscl` is a binary crate without a
//! library target, and re-implementing the parser here would fuzz something the product does not
//! run. The file is self-contained (serde_json only), so including it is honest.
//!
//! Property: for arbitrary bytes, `parse` either returns a `Result` or - the failure we are looking
//! for - panics, allocates without bound, or returns a call whose tool name is not on the allow-list.
use libfuzzer_sys::fuzz_target;

#[path = "../../cli/hscl/src/toolcall.rs"]
mod toolcall;

const ALLOW: &[&str] = &["read_doc", "update_context"];

fuzz_target!(|data: &[u8]| {
    let Ok(text) = std::str::from_utf8(data) else {
        return;
    };
    if let Ok(calls) = toolcall::parse(text, ALLOW) {
        for call in calls {
            if let toolcall::Call::Tool { name, .. } = call {
                assert!(
                    ALLOW.contains(&name.as_str()),
                    "parser returned a tool that is not on the allow-list: {name}"
                );
            }
        }
    }
});
