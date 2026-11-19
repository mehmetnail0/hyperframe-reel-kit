Same prompt, same dai transcript (cut words), seed 7, 11-19.
- gpt62sol: 42 s, $0.042, 23 beats, 8 scene types
- gemini4carbon: 34 s, $0.033, 19 beats, 13 types (first try failed only because response_format json_object + max_tokens 16000 on OpenRouter; plain call with max_tokens 32000 works)
- opus55: 122 s, 23 beats, 13 types
Render each with run.py --plan <file> on the same raw to compare.
