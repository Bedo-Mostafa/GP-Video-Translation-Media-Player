---
license: cc
language:
- ar
- en
metrics:
- bleu
- chrf
- ter
base_model:
- gimmeursocks/opus-mt-tc-big-en-ar-distilled
pipeline_tag: translation
base_model_relation: quantized
---

This model is a float16 quantized version of gimmeursocks/opus-mt-tc-big-en-ar-distilled. It achieves the following results on the testing set:
| langpair | testset | chr-F | BLEU  | TER  | #sent | #words |
|----------|---------|-------|-------|------|-------|--------|
| eng-ara | tatoeba-test-v2021-08-07 | 0.496 | 22.4 | 0.629 | 10305 | 61356 |
| eng-ara | flores101-devtest | 0.566 | 25.6 | 0.581 | 1012 | 21357 |
| eng-ara | tico19-test | 0.545 | 24.8 | 0.609 | 2100 | 51339 |