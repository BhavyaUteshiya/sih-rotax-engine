# Workspace Rules

## Disable Planning Mode & Execution Prompts
Do not use Planning Mode for this workspace. 
When given a task, just execute it directly. Do not create an `implementation_plan.md` artifact and do not stop to wait for user approval or feedback.
Additionally, when creating executable scripts or test files, DO NOT set `RequestFeedback: true` to ask the user for permission to run them. Instead, use your `run_command` tools to proactively execute the scripts yourself and just report the results back to the user.
