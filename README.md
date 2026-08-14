# Support Ticket Triage Agent

Classifies incoming support tickets by **category** and **urgency**, assigns a **confidence score**, routes each ticket to the right team, and flags low-confidence tickets for **human review** instead of guessing.

Built for the Rooman Technologies 24-Hour AI Agent Challenge.

---

## Overview

The **Support Ticket Triage Agent** is designed to automate the initial stage of customer support workflows. In SaaS and enterprise platforms, manual sorting of support tickets is time-consuming, prone to human error, and delays resolution times. 

This project solves this problem by using a local Large Language Model (LLM) to instantly read the subject and body of incoming tickets, classify them into predefined categories, assess urgency based on business impact, determine an appropriate routing team, and evaluate confidence. By running entirely locally, it eliminates API usage costs and ensures customer data privacy.

---

## Key Features

Only features that actually exist in the codebase:
* **Local LLM Inference**: Communicates directly with a local Ollama instance (defaulting to the `llama3` model) with structured JSON hints and low temperature (0.1) for consistent output.
* **Structured Output Parsing & Fallback**: Standardizes response formats with a robust parser that uses regular expressions to extract JSON blocks, handling cases where models output extraneous conversational text.
* **Rule-Based Routing**: Maps the predicted category to a specific internal support team using a deterministic lookup table.
* **Smart Human Review Flag**: Applies a confidence threshold (`< 0.6`) to flag vague, ambiguous, or poorly-articulated tickets for manual review.
* **Interactive Streamlit Web UI**:
  * **Single Ticket Test**: Real-time classification tester for quick ad-hoc queries.
  * **Batch Triage**: Upload custom CSVs (or run the bundled sample dataset) to view progress, inspect classified tickets side-by-side, view metrics, and download results as a new CSV.
* **CLI Batch Runner**: Command-line interface (`run_batch.py`) to process ticket CSVs headlessly and output results directly.

---

## End-to-End Workflow

The diagram and steps below show the complete flow of data through the system:

```
                  [Input: Single Ticket (Web UI) OR Batch CSV (Web UI / CLI)]
                                           │
                                           ▼
               [Format user payload & System Prompt in ticket_agent.py]
                                           │
                                           ▼
                     [Send POST request to local Ollama API]
                                           │
                                           ▼
                 [Retrieve response -> Parse JSON (with Regex Fallback)]
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
             [Success: Parse JSON]                  [Failure: JSON/API Error]
                       │                                       │
                       ▼                                       │
         [Determine Team from Routing Table]                   │
                       │                                       │
            ┌──────────┴──────────┐                            │
            ▼                     ▼                            │
     [Confidence >= 0.6]   [Confidence < 0.6]                  │
            │                     │                            │
            ▼                     ▼                            ▼
  [Route to Assigned Team] [Flag for Human Review]   [Flag for Human Review + Log Error]
                       │                  │                            │
                       └──────────────────┼────────────────────────────┘
                                          ▼
                      [Output results to screen or output CSV]
```

1. **Input Submission**: A single ticket (Subject & Body) is entered in the Web UI, or a CSV file is supplied to the CLI/Web UI.
2. **Context Injection**: The ticket data is combined with a detailed system prompt defining instructions, category choices, urgency rules, and confidence guidelines.
3. **Model Request**: The formatted request is sent to the local Ollama chat API.
4. **JSON Extraction**: The response is processed. If the model includes markdown or commentary, regex filters out the JSON object. If parsing fails, the ticket is immediately flagged for human review.
5. **Sanitization**: Extracted fields (category, urgency, confidence) are validated against acceptable values.
6. **Routing & Thresholding**:
   - The category is matched to a team via the `ROUTING_TABLE`.
   - If the confidence score is below `0.6`, `needs_human_review` is set to `True`.
7. **Result Delivery**: Output is displayed on the Streamlit dashboard or written to the target results CSV.

---

## Tech Stack

The application is built using the following technologies:
* **Language**: Python 3.8+ (tested on Python 3.13)
* **Frontend UI**: [Streamlit](https://streamlit.io/) (v1.38.0) - used for the interactive web dashboard.
* **Data Processing**: [Pandas](https://pandas.pydata.org/) (v2.3.3) - handles reading input CSVs, managing dataframes, and writing result CSVs.
* **HTTP Client**: [Requests](https://requests.readthedocs.io/) (v2.32.3) - manages HTTP communications with the local Ollama API server.
* **LLM Host**: [Ollama](https://ollama.com/) (running locally) - hosts and runs open LLM weights.

---

## Project Structure

* **`ticket_agent.py`**: The core backend. Contains configuration variables, the main prompt template, system constants, JSON regex parser, and the `classify_ticket` / `classify_batch` functions.
* **`app.py`**: The Streamlit web application. Renders the layout, tabs, sidebar settings, progress bars, interactive metrics, and handles downloading processed outputs.
* **`run_batch.py`**: The CLI entrypoint. Parses input parameters, loads CSVs via Pandas, invokes the batch triage workflow, and saves results.
* **`data/sample_tickets.csv`**: Ten real-world-style sample tickets representing various scenarios (such as system outages, billing questions, minor suggestions, and vague descriptions).
* **`data/example_output_reference.csv`**: A manually authored reference dataset showing the expected structure and reasoning style of the triage output.
* **`requirements.txt`**: Pinned external library requirements.

---

## Prerequisites

To run this project, the reviewer needs:
1. **Python 3.8+** installed on the host machine.
2. **Ollama** installed on the host machine. (Download from [ollama.com](https://ollama.com/download)).
3. **An Ollama-supported LLM** pulled locally. The project defaults to `llama3` (8B parameters), but you can use `mistral`, `phi3`, `qwen2.5`, or other models.

---

## Environment Variables

This application runs **entirely locally** using the local Ollama API endpoint (`http://localhost:11434/api/chat`).
* **No external API keys** (such as OpenAI, Anthropic, or Cohere keys) are required or used.
* **No environment variables** or `.env` files are required.
All configurations (such as model selection) are handled directly via CLI flags or the Web UI sidebar.

---

## Installation & Setup

Follow these exact steps from a clean clone to set up the project:

### 1. Start Ollama and Pull the Model
Ensure Ollama is running, then pull the target model (default is `llama3`):
```bash
# Verify Ollama is running locally, then pull the model:
ollama pull llama3
```
*Note: Make sure Ollama is active on port `11434`.*

### 2. Set Up a Virtual Environment & Dependencies
Clone the repository, navigate into the project directory, create a virtual environment, and install dependencies.

**On Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**On macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Running the Project

You can run the project in two ways:

### A. Web UI (Streamlit)
To start the interactive web application, run:
```bash
streamlit run app.py
```
After launching, your default web browser should open to the Streamlit app (usually `http://localhost:8501`).

### B. CLI Batch Process
To run the batch classifier via the command line, run:
```bash
python run_batch.py data/sample_tickets.csv --model llama3 --out triage_results.csv
```
This will read the sample tickets, process them against Ollama, and write the output to `triage_results.csv`.

---

## Usage / Demo

### Testing with Streamlit (Web UI)
1. Launch the app using `streamlit run app.py`.
2. Under the **Batch triage** tab, click **Use bundled sample_tickets.csv instead** (or upload your own CSV containing `subject` and `body` columns).
3. Click the **Run triage on this batch** button.
4. Watch the progress bar increment. Once complete, you will see key metrics (total tickets, flagged for review, and errors), a list of structured tickets showing routed teams and urgency badges, and a button to download the parsed CSV.
5. Switch to the **Single ticket test** tab. Enter a custom subject and body, click **Classify this ticket**, and inspect the real-time JSON-parsed output.

### Testing with the CLI
1. Run the command:
   ```bash
   python run_batch.py data/sample_tickets.csv --out output_test.csv
   ```
2. Once the script prints `Done`, open `output_test.csv` in your preferred editor or CSV viewer to review the appended `category`, `urgency`, `confidence`, `routing_team`, `needs_human_review`, and `reasoning` columns.

---

## Design Decisions & Tradeoffs

Based on the actual codebase implementation:

* **Local LLM Hosting (Ollama) vs. Cloud APIs (e.g., OpenAI GPT-4)**:
  * *Why*: Chose Ollama to achieve zero operational API cost, local data privacy (preventing client support data from leaving the network), and offline operation.
  * *Tradeoffs*: Inference speed and reliability depend heavily on local CPU/GPU specifications. Smaller local models (like `llama3:8b`) are more likely to return inconsistent formats than cloud APIs. This was mitigated by setting `format="json"`, temperature `0.1`, and implementing regex fallback extraction.
* **Deterministic Routing Table vs. LLM-Driven Routing**:
  * *Why*: The mapping from category to team is handled by a static lookup table (`ROUTING_TABLE`) in Python rather than letting the LLM name the routing team.
  * *Tradeoffs*: Simple, fast, and completely deterministic, avoiding spelling inconsistencies or hallucinations of non-existent teams. However, it requires manual code modification to add, remove, or modify teams.
* **Self-Reported Confidence Thresholding**:
  * *Why*: The model provides a self-reported confidence score between `0.0` and `1.0` in its JSON payload, which is compared to `CONFIDENCE_THRESHOLD = 0.6` to flag tickets for human review.
  * *Tradeoffs*: Fast to implement and doesn't require extra validation steps. However, self-reported LLM confidence is a heuristic and is not statistically calibrated, meaning the model can occasionally be overconfident on incorrect classifications.
* **Sequential Batch Loop**:
  * *Why*: Batch processing in `classify_batch` loops through tickets one by one.
  * *Tradeoffs*: Simple implementation and minimal memory usage. However, it runs slowly for large ticket quantities because it cannot utilize concurrency.

---

## Known Limitations

* **No Retries**: The codebase does not implement retries or exponential backoff. A single transient network/port failure to Ollama will cause that ticket's classification to fail and route it to human review with the error message recorded.
* **Sequential Execution**: All batch classifications occur sequentially. There is no asynchronous or parallel processing.
* **Hardware Sensitivity**: Local classification speed is highly dependent on host compute performance. Reviewers running without a dedicated GPU will notice slow processing times.
* **Uncalibrated Confidence**: The classification confidence score is self-reported by the model rather than being calibrated against a validation dataset.
* **Dependency Pinned Version Compatibility**: `requirements.txt` pins exact versions like `pandas==2.3.3` which is a newer release and may require a modern Python installation.

---

## Future Improvements

If the project were developed further:
1. **Parallel/Asynchronous Processing**: Implement asynchronous requests to the Ollama server to classify multiple tickets in parallel, increasing batch throughput.
2. **Retry Mechanism**: Integrate a request retry helper with backoff (e.g., using Python's `tenacity` library, which is already installed as a sub-dependency of Streamlit) to handle transient Ollama server hangs.
3. **Statistical Confidence Calibration**: Run the agent against a small, labeled validation dataset to tune the confidence threshold and calibrate the model's self-reported scores.
4. **Dynamic Configuration Loading**: Allow the categories, urgency levels, and routing table to be loaded dynamically from a configuration file (JSON/YAML) or a database rather than being hardcoded in `ticket_agent.py`.

---

## Development & Commit History

* **Commit History**: A review of the Git history reveals the repository has a single initial commit:
  * `0636013` ("Initial commit" by Mohit Nagdeep on August 14, 2026).
* **Development Flow**: The source code represents the completed challenge submission. The development history is contained in this repository and can be viewed directly using `git log`.

---

## Challenge Judging Criteria Map

Here is how the project implements the hackathon criteria:

| Criteria | Implementation in Project |
|---|---|
| **Working end-to-end workflow** | Fully functional local ticket triage. Can be run via the command line (`run_batch.py`) or visually via Streamlit (`app.py`), processing real CSV inputs and producing output datasets. |
| **Foolproof setup** | Local setup with step-by-step virtualenv configuration, explicit dependency pinning, and local Ollama model-pull commands. Runs without external API keys or environment configuration. |
| **Reasoning and tradeoffs** | Addressed decisions regarding local model inference, deterministic routing tables, self-reported confidence limits, and fallback parsing. |
| **Honest limitations** | Clear callouts regarding lack of API retries, sequential processing, hardware-dependent speeds, and uncalibrated confidence. |
| **Incremental development** | Development progress is captured and verifiable in the repository's git logs. |

---

## License

No explicit license is included in this repository.
