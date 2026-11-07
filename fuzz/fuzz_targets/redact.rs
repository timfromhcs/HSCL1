#![no_main]
//! Coverage-guided fuzzing of the redaction: whatever comes out must be stable under a second pass
//! and must not contain the planted identifiers. Includes the shipped file via `#[path]` for the same
//! reason as the parser target.
use libfuzzer_sys::fuzz_target;

#[path = "../../cli/hscl/src/redact.rs"]
mod redact;

fuzz_target!(|data: &[u8]| {
    let Ok(text) = std::str::from_utf8(data) else {
        return;
    };
    let once = redact::redact(text, "fuzzuser", "fuzzhost");
    let twice = redact::redact(&once, "fuzzuser", "fuzzhost");
    assert_eq!(once, twice, "redaction is not idempotent");
    assert!(!once.contains("fuzzuser"), "user name survived: {once}");
    assert!(!once.contains("fuzzhost"), "host name survived: {once}");
});
