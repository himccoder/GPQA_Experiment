# DeepSeek V4 Flash 0731 — GPQA Diamond Replication

## 0. Project Objective

The goal of this project is to evaluate **DeepSeek V4 Flash 0731** on the **GPQA Diamond** benchmark using **Harbor + Terminus-2** as the agent/harness infrastructure.

The target is to reproduce a GPQA Diamond result of **85%+**, with Artificial Analysis reporting approximately **91%** for the model.

The experiment must:

1. Use the canonical GPQA Diamond dataset.
2. Use Harbor's evaluation framework.
3. Use Terminus-2 as the agent/harness.
4. Use DeepSeek V4 Flash 0731 through the DeepSeek API.
5. Run the complete 198-question benchmark **3 independent times**.
6. Save the trajectory for every question in every trial.
7. Calculate accuracy for each trial.
8. Report the mean accuracy across the 3 trials.
9. Make the entire experiment reproducible from the GitHub repository.

The final repository should allow another researcher to reproduce the experiment after providing their own API/Hugging Face credentials.

---

# 1. Important Conceptual Model

Do not confuse the different components.

```text
GPQA Diamond
    |
    | 198 expert-level questions
    v
Harbor
    |
    | benchmark/task management
    v
Terminus-2
    |
    | agent/harness
    v
DeepSeek API
    |
    | model inference
    v
DeepSeek V4 Flash 0731
    |
    | answer
    v
Harbor verifier
    |
    | correct / incorrect
    v
Reward + trajectory
```

### Components

**GPQA Diamond**

* The benchmark/dataset.
* 198 questions.
* Multiple-choice questions.
* Domains include biology, physics, and chemistry.
* Each question has a correct answer.

**Harbor**

* Evaluation framework.
* Creates/runs tasks.
* Manages environments.
* Executes agents.
* Collects trajectories/results.
* Runs verification.

**Terminus-2**

* The agent/harness.
* It is NOT the model.
* It controls the interaction with the environment.
* It sends prompts/messages to the model.
* It can interact with the environment through its terminal/tmux interface.
* It produces agent trajectories.

**DeepSeek V4 Flash 0731**

* The actual language model being evaluated.
* Accessed through the DeepSeek API.

**Verifier**

* Determines whether the agent's final answer matches the ground truth.

---

# 2. Do NOT Reinvent Harbor

Before implementing custom infrastructure, inspect Harbor's existing implementation.

Harbor already has support for GPQA Diamond and Terminus-2.

The first implementation task is therefore:

> Understand and reuse the existing Harbor GPQA-Diamond adapter wherever possible.

Do NOT immediately create a custom benchmark implementation.

Inspect:

* Harbor GPQA-Diamond adapter
* GPQA task generation
* GPQA verifier
* Terminus-2 agent implementation
* trajectory output
* model/API configuration
* existing GPQA parity experiment

The goal is to modify/configure the minimum amount of code necessary.

---

# 3. Dataset

The canonical dataset is the official GPQA dataset from the benchmark authors:

`Idavidrein/gpqa`

The researcher has already obtained access through Hugging Face.

## Important

Do NOT commit the GPQA questions to the GitHub repository.

The benchmark is access-controlled and should be downloaded using the user's Hugging Face credentials.

The repository should instead contain instructions explaining how to authenticate and obtain the dataset.

Verify that the relevant GPQA Diamond subset contains:

```text
198 questions
```

Before running the model, validate:

* Number of questions = 198
* Each question has 4 answer choices
* Each question has a ground-truth answer
* No accidental duplicate questions
* Dataset is the canonical GPQA dataset
* Correct subset/configuration is being used

---

# 4. DeepSeek API

Use:

```text
DeepSeek V4 Flash 0731
```

The DeepSeek API model identifier should be verified against the current DeepSeek documentation before implementation.

Do not hard-code an API key anywhere in the repository.

Use an environment variable such as:

```bash
export DEEPSEEK_API_KEY="..."
```

or the mechanism recommended by Harbor/LiteLLM.

The API endpoint should be configurable rather than scattered throughout the code.

Conceptually:

```text
Terminus-2
    |
    v
LiteLLM / OpenAI-compatible interface
    |
    v
https://api.deepseek.com
    |
    v
DeepSeek V4 Flash 0731
```

---

# 5. First Implementation Goal: One Question

DO NOT start by running all 198 questions.

First prove that a single question works end-to-end.

Required flow:

```text
1 GPQA question
       |
       v
Harbor task
       |
       v
Terminus-2
       |
       v
DeepSeek V4 Flash 0731
       |
       v
agent reasoning
       |
       v
final answer
       |
       v
verifier
       |
       v
reward
       |
       v
trajectory
```

The first successful test must demonstrate:

* DeepSeek API authentication works.
* Terminus-2 launches.
* Terminus-2 can communicate with DeepSeek.
* The GPQA task is presented correctly.
* The model produces a final answer.
* The verifier correctly evaluates the answer.
* A trajectory is produced and persisted.
* Harbor records the result.

Do not scale until this works.

---

# 6. Oracle / Verifier Sanity Check

Before trusting model results, verify that the benchmark infrastructure itself works.

If Harbor's existing GPQA adapter provides an oracle/sanity-check mechanism, run it.

Expected conceptual result:

```text
198 / 198
100%
```

This does NOT evaluate DeepSeek.

It verifies that:

* the dataset was loaded correctly,
* questions were converted into tasks correctly,
* ground-truth answers are correct,
* answer extraction works,
* the verifier works.

If the oracle/verifier does not achieve the expected result, stop and debug the benchmark infrastructure before evaluating DeepSeek.

---

# 7. Understand the GPQA Answer Format

This is critical.

GPQA is multiple choice.

The final answer should ultimately be represented as one of:

```text
A
B
C
D
```

The verifier should compare the extracted final answer against the ground truth.

The model may produce extensive reasoning before its final answer.

Example:

```text
The relevant physical principle is...

Therefore, after calculating...

The correct answer is C.
```

The evaluation pipeline must reliably extract:

```text
C
```

Do not assume the model will always output exactly `C`.

Inspect Harbor's existing GPQA adapter to understand how answer extraction is already handled.

Prefer the existing implementation rather than creating a new parser unless necessary.

---

# 8. Terminus-2 Configuration

Start with the existing Harbor Terminus-2 configuration.

Important parameters to investigate:

```text
model_name
api_base
temperature
max_turns
reasoning_effort
max_thinking_tokens
enable_summarize
parser_name
```

Do not arbitrarily modify many parameters.

The configuration must be documented because it directly affects the benchmark result.

Create a single configuration source, for example:

```text
config/terminus2-deepseek.yaml
```

or whatever configuration format Harbor expects.

Document every non-default parameter.

---

# 9. Experimental Configuration

The experiment needs to be reproducible.

Record at minimum:

```text
Model:
DeepSeek V4 Flash 0731

Benchmark:
GPQA Diamond

Number of questions:
198

Number of trials:
3

Agent:
Terminus-2

Framework:
Harbor

Temperature:
[record exact value]

Reasoning configuration:
[record exact configuration]

Max turns:
[record exact value]

API:
DeepSeek API

Dataset version/revision:
[record exact version/commit/hash if available]

Harbor version/commit:
[record]

Terminus-2 version/commit:
[record]

Date:
[record]
```

Do not leave these values implicit.

---

# 10. Temperature and Randomness

Terminus-2 has a configurable temperature.

Do not blindly change the default.

First determine what configuration is intended for the replication.

If temperature is nonzero, different runs can produce different answers.

That is one reason the experiment requires 3 trials.

The final report must preserve the exact temperature.

If possible, also record:

* random seed
* model generation parameters
* API parameters

If the API/model does not provide deterministic seeding, document that.

---

# 11. Artificial Analysis Comparison

The purpose is NOT necessarily to reproduce exactly 91%.

The practical target from the task description is:

```text
85%+
```

Artificial Analysis reports approximately:

```text
91%
```

The experiment should therefore report:

```text
Artificial Analysis:
~91%

Our experiment:
Trial 1 = X/198
Trial 2 = Y/198
Trial 3 = Z/198

Mean = X%
```

Do not claim that a difference from 91% means the model itself is better/worse.

Differences can arise from:

* prompt
* harness
* temperature
* reasoning settings
* answer extraction
* model/API version
* benchmark version
* sampling
* tool access
* context management

The README should explicitly state that this is a replication/evaluation under the specified Harbor + Terminus-2 setup.

---

# 12. Trial Structure

Run exactly 3 full trials.

Each trial should evaluate all 198 questions.

Therefore:

```text
3 × 198 = 594
```

total task executions.

Directory structure should clearly separate trials:

```text
trajectories/
├── trial-1/
│   ├── question-001/
│   ├── question-002/
│   └── ...
│
├── trial-2/
│   ├── question-001/
│   ├── question-002/
│   └── ...
│
└── trial-3/
    ├── question-001/
    ├── question-002/
    └── ...
```

Use Harbor's native trajectory format/storage wherever possible.

Do not invent a second trajectory format unless required.

---

# 13. Run Small Tests Before Full Evaluation

Use progressive testing.

### Test 1

```text
1 question
```

### Test 2

```text
5 questions
```

### Test 3

```text
10 questions
```

### Test 4

```text
20 questions
```

### Test 5

```text
198 questions
```

Only move to the next stage once the previous stage works correctly.

This prevents wasting API credits/time debugging a problem after 198 failed runs.

---

# 14. Full Trial Execution

Once the small tests pass:

```text
Trial 1:
198 questions

Trial 2:
198 questions

Trial 3:
198 questions
```

The execution should be resumable if possible.

If question 147 fails because of an API/network error, do not necessarily restart all 198 questions.

Investigate whether Harbor supports:

* task retries
* failed-task reruns
* resumable runs

Use those mechanisms if available.

---

# 15. Results Calculation

For each trial calculate:

```text
accuracy = number_correct / 198
```

Example:

```text
Trial 1:
172 / 198 = 86.87%

Trial 2:
170 / 198 = 85.86%

Trial 3:
174 / 198 = 87.88%
```

Then:

```text
mean_accuracy =
    (trial1_accuracy +
     trial2_accuracy +
     trial3_accuracy) / 3
```

Do not simply pool all answers unless explicitly desired.

Report both:

```text
per-trial accuracy
```

and:

```text
mean of the three trial accuracies
```

Also report raw counts:

```text
Trial 1: 172/198
Trial 2: 170/198
Trial 3: 174/198
Mean: 86.87%
```

---

# 16. Results File

Create a machine-readable results file.

Example:

```json
{
  "benchmark": "GPQA-Diamond",
  "num_questions": 198,
  "num_trials": 3,
  "model": "DeepSeek V4 Flash 0731",
  "agent": "Terminus-2",
  "trials": [
    {
      "trial": 1,
      "correct": 172,
      "total": 198,
      "accuracy": 0.8687
    },
    {
      "trial": 2,
      "correct": 170,
      "total": 198,
      "accuracy": 0.8586
    },
    {
      "trial": 3,
      "correct": 174,
      "total": 198,
      "accuracy": 0.8788
    }
  ],
  "mean_accuracy": 0.8687
}
```

The exact values above are ONLY an example. Do not use them as actual results.

---

# 17. Trajectory Requirements

The trajectory is a major deliverable.

For every question, preserve the agent execution produced by Terminus-2/Harbor.

The trajectory should allow us to understand:

```text
Question
    ↓
Agent/model interaction
    ↓
Tool/terminal interactions
    ↓
Reasoning/actions
    ↓
Final answer
    ↓
Reward/verifier result
```

Do not manually create fake trajectory files.

Use the native Harbor/Terminus-2 trajectory output.

After the experiment, verify:

```text
Trial 1:
198 trajectories

Trial 2:
198 trajectories

Trial 3:
198 trajectories
```

Total:

```text
594 trajectories
```

If Harbor stores failed/invalid trajectories differently, document that explicitly.

---

# 18. Repository Structure

Aim for something similar to:

```text
deepseek-gpqa-replication/
│
├── README.md
├── IMPLEMENTATION_PLAN.md
├── .gitignore
│
├── config/
│   └── terminus2-deepseek.yaml
│
├── scripts/
│   ├── run_trial.sh
│   ├── run_all_trials.sh
│   └── calculate_results.py
│
├── results/
│   ├── trial-1.json
│   ├── trial-2.json
│   ├── trial-3.json
│   └── summary.json
│
├── trajectories/
│   ├── trial-1/
│   ├── trial-2/
│   └── trial-3/
│
└── docs/
    └── experiment-notes.md
```

Do not commit:

```text
.env
API keys
Hugging Face tokens
GPQA question data
unnecessary Docker images
large caches
Python virtual environments
```

Add appropriate entries to `.gitignore`.

---

# 19. README Requirements

The final README should explain:

## What this project does

One paragraph describing the replication.

## Architecture

Explain:

```text
GPQA → Harbor → Terminus-2 → DeepSeek → verifier
```

## Requirements

List:

* Python version
* Harbor
* Docker
* Hugging Face account/access
* DeepSeek API key
* required CLI tools

## Setup

Give exact commands.

## Authentication

Explain:

```text
Hugging Face authentication
DeepSeek API authentication
```

Never put actual credentials in the repository.

## Running one test

Provide the exact command.

## Running a trial

Provide the exact command.

## Running all 3 trials

Provide the exact command.

## Results

Show the final measured results.

## Reproducibility

Document:

* model
* model version
* dataset
* Harbor version
* Terminus-2 version
* configuration
* temperature
* reasoning settings
* date
* number of trials

---

# 20. Logging

Every run should record enough information to debug failures.

At minimum capture:

```text
task ID
question ID
trial
model
start time
end time
success/failure
final answer
ground truth
reward
error, if any
trajectory location
```

If API errors occur, preserve the error information without exposing API credentials.

---

# 21. Failure Handling

Expect failures.

Potential issues include:

* DeepSeek API errors
* rate limits
* timeout
* malformed model output
* Harbor task failure
* Docker failure
* Terminus-2 failure
* answer extraction failure
* missing trajectory
* network failure

Do not silently treat infrastructure failures as incorrect answers.

Distinguish:

```text
model answered incorrectly
```

from:

```text
task failed due to infrastructure/API error
```

If a task fails because of infrastructure, investigate whether it should be retried according to the experimental protocol.

Document any retries.

---

# 22. Cost / API Usage

Before launching 594 tasks, estimate API usage.

Do a small test first.

Record approximately:

```text
1 question → tokens/cost
10 questions → tokens/cost
198 questions → estimated cost
594 questions → estimated total cost
```

Do not accidentally launch the full benchmark multiple times while debugging.

---

# 23. Evaluation Integrity

Avoid modifying the benchmark questions.

Do not:

* change answer choices
* remove difficult questions
* give the model ground truth
* manually correct model answers
* selectively rerun only questions it got wrong
* use Google/search manually during evaluation
* alter the prompt after seeing results without documenting it

If the experimental configuration changes, treat it as a different experiment.

---

# 24. Before Running the Real Experiment

Create a checklist and verify all of the following:

```text
[ ] Official GPQA Diamond dataset access works
[ ] Correct dataset contains 198 questions
[ ] Harbor installed
[ ] Docker works
[ ] Terminus-2 works independently
[ ] DeepSeek API key works
[ ] DeepSeek V4 Flash 0731 is the actual model being called
[ ] DeepSeek endpoint is correct
[ ] Harbor can route requests to DeepSeek
[ ] One GPQA question succeeds
[ ] Verifier succeeds
[ ] Oracle/sanity test succeeds if available
[ ] Trajectory is generated
[ ] Trajectory is persisted
[ ] 5-question test succeeds
[ ] 10-question test succeeds
[ ] Configuration is frozen
[ ] Experiment configuration is documented
[ ] API cost is understood
[ ] Git repository is clean
```

Only after all of these are satisfied should Trial 1 begin.

---

# 25. Final Deliverables

The final GitHub repository must contain:

### Code

Everything required to reproduce the evaluation.

### Configuration

Exact Terminus-2 + DeepSeek configuration.

### Experiment scripts

Commands/scripts to run:

```text
single test
trial
all 3 trials
result calculation
```

### Trajectories

```text
3 × 198
```

agent trajectories.

### Results

Per-trial and aggregate results.

### Documentation

Clear setup and reproduction instructions.

---

# 26. Final Report Format

The final README should contain a table similar to:

| Trial    | Correct | Total | Accuracy |
| -------- | ------: | ----: | -------: |
| 1        |       X |   198 |       X% |
| 2        |       X |   198 |       X% |
| 3        |       X |   198 |       X% |
| **Mean** |       — |     — |   **X%** |

Then compare against:

```text
Artificial Analysis: ~91%
Our result: X%
Target: >85%
```

Explain any significant difference.

---

# 27. Claude Code Instructions

Claude Code should follow this implementation strategy:

### Step 1

Inspect the existing Harbor repository and documentation.

Find:

```text
GPQA-Diamond adapter
Terminus-2 implementation
model configuration
trajectory implementation
verifier
existing parity experiment
```

Do not implement a duplicate system if Harbor already provides it.

### Step 2

Determine the exact Harbor command/configuration required to run:

```text
1 GPQA question
+
Terminus-2
+
DeepSeek V4 Flash 0731
```

### Step 3

Configure DeepSeek using environment variables.

Never hard-code credentials.

### Step 4

Run a one-question smoke test.

Inspect the complete trajectory and verifier result.

### Step 5

Run the verifier/oracle sanity check if supported.

### Step 6

Run 5 and 10 question tests.

### Step 7

Freeze the experimental configuration.

Do not change model parameters after Trial 1 begins unless starting a new explicitly documented experiment.

### Step 8

Run Trial 1.

### Step 9

Run Trial 2.

### Step 10

Run Trial 3.

### Step 11

Calculate and validate all results.

### Step 12

Verify that 594 question trajectories are present.

### Step 13

Clean the repository.

Remove:

* secrets
* caches
* virtual environments
* GPQA data
* temporary files

### Step 14

Update README with exact reproduction instructions and measured results.

---

# 28. Important Principle

The objective is not to write the most code.

The objective is to produce a **scientifically defensible and reproducible evaluation**.

Prefer:

```text
existing Harbor implementation
        +
small configuration layer
        +
small experiment scripts
```

over:

```text
custom benchmark implementation
+
custom agent
+
custom verifier
```

unless Harbor's existing implementation genuinely cannot support the required experiment.

Every custom modification should have a reason documented in the repository.

---

# 29. Immediate Next Action

Before writing significant code:

1. Inspect the existing Harbor GPQA-Diamond adapter.
2. Inspect the existing Harbor Terminus-2 implementation.
3. Inspect the existing Harbor GPQA parity experiment.
4. Determine the exact command/configuration for running one GPQA task with Terminus-2.
5. Configure DeepSeek V4 Flash 0731.
6. Run ONE question successfully.
7. Inspect the resulting trajectory.

Only after this is working should the implementation proceed to the 198-question benchmark.
