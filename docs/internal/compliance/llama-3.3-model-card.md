# Meta Llama 3.3 70B — Model Card (Summary for Compliance)

**Source:** https://github.com/meta-llama/llama-models/blob/main/models/llama3_3/MODEL_CARD.md
**Retrieved:** 2026-08-14
**Provider:** Meta (accessed via Groq API)

## Key Specifications

| Attribute | Value |
|-----------|-------|
| **Model** | Llama 3.3 70B Instruct |
| **Developer** | Meta |
| **Architecture** | Auto-regressive transformer, GQA |
| **Parameters** | 70B |
| **Context Length** | 128k tokens |
| **Training Data** | ~15T tokens (publicly available sources) |
| **Knowledge Cutoff** | December 2023 |
| **Release Date** | December 6, 2024 |
| **License** | Llama 3.3 Community License Agreement (custom commercial license) |
| **Supported Languages** | English, German, French, Italian, Portuguese, Hindi, Spanish, Thai |

## License

Custom commercial license: **Llama 3.3 Community License Agreement**.
- Permits commercial use (with restrictions: >700M monthly active users require separate license)
- QA-FRAMEWORK (SabaTech) is well below the MAU threshold → commercial use permitted

## Intended Use

Per Meta: "Llama 3.3 is intended for commercial and research use in multiple languages. Instruction tuned text only models are intended for assistant-like chat."

QA-FRAMEWORK use case (AI-powered test generation, vulnerability analysis assistance) falls within intended commercial use.

## Safety

Meta applied SFT + RLHF alignment. Model has safety fine-tuning. Developers responsible for application-level safety (QA-FRAMEWORK implements its own input/output validation).

## GPAI Classification

Llama 3.3 70B qualifies as a GPAI model under EU AI Act definitions (general-purpose, large-scale, capable of serving a variety of downstream tasks).

## Conclusion

✅ **License permits QA-FRAMEWORK use.** Community License allows commercial automated testing. No conflict identified.
