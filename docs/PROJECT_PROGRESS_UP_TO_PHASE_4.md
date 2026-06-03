# Home Loan AI Journey Project — Question and Answer Notes up to Phase 4

## Section 1: Project Overview

### Q1. What is the Home Loan AI Journey project?

**Answer:**
The Home Loan AI Journey project is a backend prototype that performs an initial home-loan assessment. It collects applicant details, loan details, property information and document status, then calculates affordability metrics, applies rule-based checks, generates AI-based explanations and records execution traces using Opik.

The current project is an initial assessment system and does not represent final approval from a real bank.

---

### Q2. What problem is this project trying to solve?

**Answer:**
A home-loan applicant normally needs to understand:

* whether they may be eligible for a loan;
* whether the requested loan amount is affordable;
* which documents are required;
* why an application may be rejected or sent for review;
* what action they should take next.

The project tries to make this initial journey structured and easier to understand by combining calculations, business rules, workflow orchestration and AI-generated explanations.

---

### Q3. Who can use this system?

**Answer:**
The current prototype can be used by:

* a customer who wants an initial home-loan assessment;
* a loan officer who wants a quick internal summary;
* a developer or reviewer who wants to inspect how the application decision was reached.

In its current version, it runs through terminal input and is intended for development and demonstration.

---

### Q4. Is this a final home-loan approval system?

**Answer:**
No. It is only an initial prototype assessment system.

The current underwriting thresholds are project-level prototype rules. A real production system would require:

* verified lender policies;
* legal and compliance checks;
* secure customer-data handling;
* actual document verification;
* human officer review;
* final sanction and disbursement processes.

---

## Section 2: What Was Built Initially and Why It Was Upgraded

### Q5. What did the first version of the project do?

**Answer:**
The first version was a simple home-loan eligibility checker. It accepted basic details such as:

* applicant name;
* age;
* income;
* employment type;
* loan amount;
* credit score;
* existing EMI;
* submitted documents.

It then performed basic checks and returned a result such as approved, rejected or missing documents.

---

### Q6. Why was the first version not enough?

**Answer:**
The first version was too basic because a realistic home-loan journey involves more than a simple eligibility result.

It needed to include:

* proper property details;
* dynamic document requirements;
* EMI and affordability calculations;
* structured underwriting rules;
* multiple decision outcomes;
* customer-facing explanations;
* internal review summaries;
* workflow tracing and debugging.

That is why the project was upgraded into a more modular and realistic workflow.

---

### Q7. What major improvements were added after the first version?

**Answer:**
The following improvements were added:

1. Modular project structure using separate nodes, services and prompt files.
2. Interactive input for customer, loan and property information.
3. Dynamic document checklist generation.
4. EMI, LTV, DTI and FOIR calculations.
5. Multiple underwriting outcomes:

   * `pre_approved`
   * `needs_documents`
   * `manual_review`
   * `rejected`
6. Detailed decision reasons, risk flags, positive factors and recommended actions.
7. LangChain and Ollama integration for customer explanation and officer summary.
8. Local Opik tracing through Docker.
9. Maximum eligible loan estimation and requested-loan affordability gap calculation.

---

## Section 3: Current End-to-End Workflow

### Q8. What is the current user journey in the project?

**Answer:**
The current journey is:

```text
User enters customer details
        ↓
User enters loan requirement details
        ↓
User enters property details
        ↓
System generates required document checklist
        ↓
User confirms submitted documents
        ↓
System calculates EMI, LTV, DTI and FOIR
        ↓
System estimates maximum eligible loan amount
        ↓
System verifies missing documents
        ↓
Rule engine performs initial underwriting assessment
        ↓
System decides:
    - pre_approved
    - needs_documents
    - manual_review
    - rejected
        ↓
LangChain + Ollama generate:
    - customer explanation
    - officer summary
        ↓
Opik traces the workflow execution and LLM calls
```

---

### Q9. What details does the user currently enter?

**Answer:**
The user enters four categories of information.

#### Customer Details

* applicant name;
* age;
* employment type;
* monthly income;
* work experience;
* credit score;
* existing EMI.

#### Loan Details

* requested loan amount;
* interest rate;
* tenure;
* loan purpose.

#### Property Details

* property value;
* property type;
* property location;
* property age;
* construction status;
* legal clearance status;
* valuation status.

#### Document Details

The system dynamically asks whether required documents have been submitted.

---

## Section 4: Technology Stack

### Q10. Which technologies are being used?

**Answer:**

| Technology                | Purpose                                       |
| ------------------------- | --------------------------------------------- |
| Python                    | Backend development language                  |
| LangGraph                 | Controls the workflow, state and branching    |
| LangChain                 | Connects prompts with the local LLM           |
| Ollama with `llama3.2:3b` | Runs the local language model                 |
| Opik                      | Records execution traces and LLM observations |
| Docker Desktop            | Runs the local Opik platform                  |
| Git and GitHub            | Version control and branch/PR management      |

---

### Q11. Why was Ollama used instead of OpenAI?

**Answer:**
Initially, OpenAI was considered for the LLM layer. However, the OpenAI API account produced a quota error during testing.

To continue development without paid API dependency, the project was shifted to:

```text
LangChain + ChatOllama + llama3.2:3b
```

Ollama allows the model to run locally and still supports the LLM explanation feature required for the project.

---

## Section 5: LangGraph Understanding

### Q12. Why was LangGraph used in this project?

**Answer:**
LangGraph was used because a home-loan journey is a multi-step workflow where data moves through different checks and the next step depends on the result.

For example:

* financial metrics must be calculated before affordability is assessed;
* documents must be checked before deciding whether processing can continue;
* the decision determines whether the path is pre-approval, missing documents, manual review or rejection.

LangGraph makes this workflow structured using:

* state;
* nodes;
* edges;
* conditional routing.

It also makes future additions easier, such as human review, policy Q&A, document upload or scenario comparison.

---

### Q13. What is the state in LangGraph?

**Answer:**
The state is the shared data object passed between workflow nodes.

In this project, `HomeLoanState` stores:

* applicant information;
* loan information;
* property information;
* document information;
* calculated financial metrics;
* underwriting result;
* risk analysis;
* AI-generated outputs.

Every node reads the fields it needs and updates the state with new results for later nodes.

---

### Q14. How is state passed between nodes?

**Answer:**
When the workflow starts, `main.py` creates an application dictionary containing the user input and empty result fields.

LangGraph passes this state through the workflow. For example:

```text
Initial State
    ↓
calculate_financial_metrics adds EMI, LTV, DTI, FOIR and eligibility estimate
    ↓
verify_documents adds required documents and missing documents
    ↓
underwriting_decision adds decision, risk flags and recommendations
    ↓
LLM nodes add customer explanation and officer summary
```

This allows all later nodes to use the results generated by earlier nodes.

---

### Q15. What is a node in this project?

**Answer:**
A node is one step in the workflow. Each node performs one main responsibility.

Examples:

| Node                            | Responsibility                                   |
| ------------------------------- | ------------------------------------------------ |
| `calculate_financial_metrics`   | Calculates EMI, LTV, DTI, FOIR and loan estimate |
| `verify_documents`              | Checks required and missing documents            |
| `underwriting_decision`         | Applies decision rules                           |
| `decision_router`               | Routes to the correct decision path              |
| `generate_customer_explanation` | Creates customer-friendly explanation            |
| `generate_officer_summary`      | Creates internal officer summary                 |

---

### Q16. What do edges do in LangGraph?

**Answer:**
Edges connect one workflow step to the next.

For example:

```python
workflow.add_edge("calculate_financial_metrics", "verify_documents")
```

means that after the financial calculation node completes, the workflow moves to document verification.

---

### Q17. What is conditional routing?

**Answer:**
Conditional routing is used when the next path depends on the decision.

For example:

```text
pre_approved     → approval response
needs_documents  → document request response
manual_review    → review response
rejected         → rejection response
```

This is useful because all applicants should not receive the same next step.

---

## Section 6: File-by-File Understanding

### Q18. What does `main.py` do?

**Answer:**
`main.py` is the starting point of the application.

It:

* configures local Opik settings;
* collects user input;
* validates fixed-choice inputs;
* creates the initial application state;
* runs the compiled LangGraph workflow;
* displays the final output;
* flushes pending Opik traces before the program ends.

---

### Q19. What does `state.py` do?

**Answer:**
`state.py` defines the structure of the shared data passed through the workflow.

It contains fields for:

* applicant details;
* loan details;
* property details;
* document information;
* financial metrics;
* eligibility estimation;
* underwriting analysis;
* AI outputs.

---

### Q20. What does `graph.py` do?

**Answer:**
`graph.py` builds the LangGraph workflow.

It:

* creates the state graph;
* registers nodes;
* connects nodes using edges;
* defines conditional routing;
* compiles the graph so that it can be run from `main.py`.

---

### Q21. What does `nodes/financial_nodes.py` do?

**Answer:**
This node calls the calculation services and adds financial results to the workflow state.

It calculates:

* proposed EMI;
* LTV ratio;
* DTI ratio;
* FOIR ratio;
* maximum affordable new EMI;
* estimated maximum eligible loan;
* requested loan amount gap.

---

### Q22. What does `nodes/document_nodes.py` do?

**Answer:**
This node checks document requirements.

It:

* generates the required document list based on employment type and property type;
* compares required documents with submitted documents;
* stores missing documents;
* sets document status as complete or incomplete.

---

### Q23. What does `nodes/decision_nodes.py` do?

**Answer:**
This file contains the deterministic underwriting node and router.

The underwriting node calls the rule engine and stores:

* final initial decision;
* risk level;
* decision reasons;
* risk flags;
* positive factors;
* recommended actions.

The router sends the state down the appropriate outcome path.

---

### Q24. What does `nodes/llm_nodes.py` do?

**Answer:**
This file uses LangChain and Ollama for generating text outputs.

It contains:

* customer explanation generation;
* officer summary generation.

The LLM does not make the loan decision. It receives the already calculated values and rule-engine facts, then formats them into understandable text.

---

### Q25. What does `services/emi_calculator.py` do?

**Answer:**
It calculates the proposed monthly EMI using:

* requested loan amount;
* interest rate;
* tenure.

---

### Q26. What does `services/ltv_calculator.py` do?

**Answer:**
It calculates the loan-to-value ratio, which compares the requested loan amount with the property value.

---

### Q27. What does `services/dti_calculator.py` do?

**Answer:**
It calculates how much of the applicant’s monthly income would be used for total EMI obligations.

It includes:

* existing EMI;
* proposed home-loan EMI;
* monthly income.

---

### Q28. What does `services/eligibility_calculator.py` do?

**Answer:**
This service was added in Phase 4.

It estimates:

* maximum EMI capacity available for a new loan;
* approximate maximum eligible loan amount;
* the gap between the requested amount and estimated eligible amount.

It uses a prototype FOIR assumption of 45% of monthly income.

---

### Q29. What does `services/rule_engine.py` do?

**Answer:**
The rule engine makes the prototype underwriting decision.

It checks:

* age;
* income;
* credit score;
* DTI;
* LTV;
* document completion;
* legal clearance;
* valuation status;
* requested amount compared with estimated eligibility.

It produces deterministic facts that the LLM later explains.

---

### Q30. What does `services/document_service.py` do?

**Answer:**
It generates a document checklist depending on the applicant and property type.

For example:

* salaried applicants require salary-related documents;
* self-employed applicants require business/income-tax-related documents;
* apartments or flats require different property documents from plots or houses.

---

### Q31. What do the prompt files do?

**Answer:**
The prompt files control how the local LLM writes the final text.

#### `prompts/explanation_prompt.py`

Used for the customer-facing result explanation.

#### `prompts/officer_summary_prompt.py`

Used for the internal officer summary.

The prompts were improved so that the LLM must use only supplied facts and must not invent policies, values or unsupported conclusions.

---

## Section 7: Calculations Implemented

### Q32. What is EMI and how is it used?

**Answer:**
EMI is the estimated monthly instalment for the requested home loan.

It is calculated using:

* loan amount;
* annual interest rate;
* tenure.

This is important because the system uses the proposed EMI when checking whether the applicant can afford the loan.

---

### Q33. What is LTV?

**Answer:**
LTV means Loan-to-Value ratio.

Formula:

```text
LTV = Requested Loan Amount / Property Value × 100
```

Example:

```text
Requested Loan Amount = ₹60,00,000
Property Value = ₹75,00,000
LTV = 80%
```

A very high LTV means the user is asking for a loan covering most or more than the property value.

---

### Q34. What is DTI?

**Answer:**
DTI means Debt-to-Income ratio.

In the current prototype:

```text
DTI = (Existing EMI + Proposed EMI) / Monthly Income × 100
```

It helps determine whether the customer can afford the total EMI burden.

---

### Q35. What is FOIR in the project?

**Answer:**
FOIR represents the Fixed Obligations to Income Ratio.

In the current project, FOIR is currently represented using the same total EMI burden calculation as DTI.

This is acceptable for the current prototype, but in a more detailed production implementation, the terminology and included obligations should be clarified according to the lender’s policy.

---

### Q36. What was added in Phase 4?

**Answer:**
Phase 4 added maximum eligible loan estimation.

The system now calculates:

* maximum affordable new EMI;
* estimated maximum eligible loan;
* requested amount above the eligibility estimate.

This allows the application to give a more useful output than only “approved” or “rejected”.

---

### Q37. How is maximum eligible loan calculated?

**Answer:**
The current prototype assumes:

```text
Maximum total EMI obligations = 45% of monthly income
```

Then:

```text
Maximum Affordable New EMI = Maximum Total EMI - Existing EMI
```

The system uses that available EMI capacity, together with interest rate and tenure, to estimate the maximum loan principal the applicant may be able to afford.

Important note:

```text
This is a prototype estimate, not an actual sanctioned loan amount.
```

---

### Q38. What does loan amount gap mean?

**Answer:**
Loan amount gap shows how much the requested loan exceeds the estimated maximum eligible loan.

Example:

```text
Requested Loan Amount = ₹60,00,000
Estimated Eligible Loan = ₹24,77,463
Loan Amount Gap = ₹35,22,537
```

This helps the applicant understand how much they may need to reduce the request by.

---

## Section 8: Underwriting and Business Rules

### Q39. Who makes the loan decision: Python or the LLM?

**Answer:**
Python makes the decision.

The LLM is not allowed to approve or reject the application independently.

The Python rule engine decides the outcome based on calculations and prototype rules. The LLM only explains the already-determined result.

---

### Q40. What decisions can the current system return?

**Answer:**

| Decision          | Meaning                                                            |
| ----------------- | ------------------------------------------------------------------ |
| `pre_approved`    | Applicant currently meets initial prototype conditions             |
| `needs_documents` | Application may proceed only after required documents are provided |
| `manual_review`   | Some conditions need further officer review                        |
| `rejected`        | Application fails one or more hard prototype checks                |

---

### Q41. What are the current prototype rules?

**Answer:**

| Rule                                        | Prototype Behaviour                        |
| ------------------------------------------- | ------------------------------------------ |
| Age below 21                                | Rejection reason                           |
| Monthly income below 30000                  | Rejection reason                           |
| Credit score below 650                      | Rejection reason                           |
| Credit score from 650 to below 700          | Manual review                              |
| DTI above 55%                               | Rejection reason                           |
| DTI from 45% to 55%                         | Manual review                              |
| LTV above 90%                               | Review/risk flag                           |
| Missing documents                           | Needs-documents issue                      |
| Legal clearance not clear                   | Review issue                               |
| Valuation status not clear                  | Review issue                               |
| Requested amount above eligibility estimate | Affordability risk flag and recommendation |

---

### Q42. How does the final decision priority work?

**Answer:**
The current decision priority is:

```text
If a hard rejection reason exists → rejected
Else if documents are missing → needs_documents
Else if review issues exist → manual_review
Else → pre_approved
```

This means an application with both missing documents and very high DTI will be rejected because the affordability issue is more serious than document completion.

---

### Q43. What are risk flags?

**Answer:**
Risk flags are problems identified by the rule engine.

Examples:

* DTI is above the prototype limit;
* requested amount is above estimated eligibility;
* documents are missing;
* property valuation is pending.

---

### Q44. What are positive factors?

**Answer:**
Positive factors are conditions that the applicant satisfies.

Examples:

* credit score is within acceptable range;
* DTI is within acceptable range;
* LTV is within acceptable range;
* all required documents have been submitted;
* property legal clearance is clear.

---

### Q45. What are recommended actions?

**Answer:**
Recommended actions are next-step suggestions based on the rule-engine result.

Current examples include:

* reduce existing obligations or requested loan amount;
* submit missing documents;
* complete pending property verification;
* improve the credit profile;
* proceed to final lender review after pre-approval.

A more detailed personalised recommendation engine is planned for Phase 5 but has not been started yet.

---

## Section 9: LangChain and Ollama

### Q46. Why is LangChain used?

**Answer:**
LangChain is used to connect:

* prompt templates;
* state data;
* the local Ollama language model.

It helps structure how the calculated facts are passed into the LLM for generating readable explanations.

---

### Q47. What does Ollama do?

**Answer:**
Ollama runs the local LLM model:

```text
llama3.2:3b
```

It generates:

* customer explanation;
* officer summary.

It does not calculate financial values and does not make the underwriting decision.

---

### Q48. Why is a local model useful in this project?

**Answer:**
A local model is useful because:

* it avoids paid API dependency during development;
* it can run without sending requests to OpenAI;
* it still allows integration of an LLM explanation layer;
* it is suitable for testing workflow and tracing behaviour.

---

### Q49. What problems were initially seen in LLM outputs?

**Answer:**
Earlier LLM outputs sometimes:

* invented placeholder information;
* asked for documents even when all documents were complete;
* described low DTI or FOIR as high;
* changed numeric values in the summary;
* suggested only document submission even when the application failed financial checks.

---

### Q50. How were LLM-output problems reduced?

**Answer:**
The prompts were improved so the LLM receives factual fields already produced by Python:

* decision reasons;
* risk flags;
* positive factors;
* recommended actions;
* financial metrics;
* maximum eligible loan estimate;
* missing documents.

The prompts also instruct the LLM:

* not to invent values;
* not to reinterpret calculations;
* not to change the decision;
* not to claim final approval;
* to use only supplied recommendations.

---

## Section 10: Opik and Observability

### Q51. Why was Opik used?

**Answer:**
Opik was used to trace and observe the application workflow.

It helps answer:

* which nodes ran;
* what input and output each node produced;
* where an exception happened;
* what prompt and model output were produced;
* whether the complete home-loan flow executed correctly.

---

### Q52. How was Opik initially used?

**Answer:**
Initially, Opik Cloud was configured and traces were sent to a cloud project.

Later, the requirement changed to running Opik locally.

---

### Q53. How does the current local Opik setup work?

**Answer:**
Docker Desktop runs the local Opik services.

The Python home-loan application runs separately through Terminal.

Current structure:

```text
Docker Desktop → Runs Opik services
Browser localhost:5293 → Displays Opik dashboard
Terminal python main.py → Runs Home Loan workflow
```

The application sends traces to the local Opik instance.

---

### Q54. What parts are traced in Opik?

**Answer:**
The project traces:

* overall home-loan journey;
* financial calculation node;
* EMI/LTV/DTI/eligibility calculation services;
* document verification;
* underwriting decision;
* customer explanation generation;
* officer summary generation;
* LangChain and Ollama calls.

---

### Q55. Why is Opik useful during development?

**Answer:**
Opik is useful because the workflow contains many stages and AI calls.

It helped identify:

* incorrect state values;
* errors in calculations;
* failed node execution;
* prompt-variable errors;
* incorrect LLM outputs;
* project configuration issues.

---

## Section 11: Bugs and Learning

### Q56. What major bugs occurred during development?

**Answer:**

| Bug                              | What Happened                                                               |
| -------------------------------- | --------------------------------------------------------------------------- |
| Incorrect node/function naming   | Python imports failed because function names did not match                  |
| `nodes.py` and `nodes/` conflict | Modular code imports became confusing                                       |
| Wrong Opik decorator argument    | Used `nam=` instead of `name=`                                              |
| OpenAI quota error               | API call failed due to insufficient quota                                   |
| Opik project mismatch            | Traces were sent under `Default Project` instead of the required project    |
| Invalid free-text input          | Typo such as `alaried` was treated as another employment category           |
| LLM hallucinated conclusions     | Summary changed facts or misunderstood ratios                               |
| Phase 3 unpacking error          | Rule engine returned more values than the node expected                     |
| Phase 4 key-name error           | `maximum_affordable_new_emi` and `max_affordable_new_emi` were inconsistent |
| Missing prompt variables         | Prompt expected Phase 4 values that were not passed into the LLM node       |

---

### Q57. What did I learn from fixing these bugs?

**Answer:**
The main learning points were:

* Python import and function names must match exactly.
* LangGraph state needs to be updated consistently whenever new fields are introduced.
* A rule engine should determine business decisions, not an LLM.
* LLM prompts must be grounded with factual values.
* Tracing is useful for debugging multi-step workflow systems.
* Feature additions should be tested before moving to later phases.
* Git branches and commits help preserve working milestones.

---

## Section 12: Testing

### Q58. How has the project been tested so far?

**Answer:**
The project has been manually tested through terminal inputs for different application scenarios.

Scenarios tested include:

* rejected applicant with high DTI;
* rejected applicant with missing documents and valuation issues;
* loan request above estimated eligibility;
* pre-approval style scenarios;
* document checklist behaviour;
* Opik trace visibility.

---

### Q59. Which test cases should still be formally recorded?

**Answer:**

| Test Case                                         | Expected Outcome                              |
| ------------------------------------------------- | --------------------------------------------- |
| Strong applicant with complete documents          | `pre_approved`                                |
| Strong financial values but missing documents     | `needs_documents`                             |
| Good financial values but pending property checks | `manual_review`                               |
| Low income or low credit score                    | `rejected`                                    |
| Very high DTI                                     | `rejected`                                    |
| Loan above estimated eligibility                  | Affordability risk flag and loan-gap guidance |
| Invalid employment/property input                 | Input rejected and requested again            |

---

### Q60. How would unit tests be added later?

**Answer:**
Unit tests can be added for each calculation and rule separately.

Examples:

* test EMI output for known loan values;
* test LTV calculation;
* test DTI calculation;
* test maximum eligible loan calculation;
* test rejection for low credit score;
* test manual review for pending valuation;
* test missing-document route;
* test pre-approved route.

---

## Section 13: Deployment and Production Thinking

### Q61. How is the project currently run?

**Answer:**
Currently:

```text
Home-loan application → runs locally using python main.py
Ollama model → runs locally
Opik dashboard → runs locally through Docker Desktop
GitHub → stores code and branch progress
```

---

### Q62. How could this be deployed later?

**Answer:**
A future deployment could include:

* Streamlit UI for a simple demo;
* FastAPI backend for API-based access;
* React frontend for a more polished user interface;
* Dockerised backend services;
* cloud deployment for the web app;
* secure storage/database for application records;
* controlled observability setup.

---

### Q63. What would need improvement before using this in production?

**Answer:**
Before production use, the system would need:

* real lender-approved underwriting policies;
* secure authentication;
* encryption and privacy controls;
* proper document upload and validation;
* fraud and identity checks;
* audit logs;
* human review before final sanction;
* automated tests;
* model safety checks;
* database storage;
* monitoring and deployment security.

---

## Section 14: Current Completion Status

### Q64. What work is completed so far?

**Answer:**
Completed up to Phase 4:

* modular LangGraph workflow;
* interactive terminal input;
* validated categorical inputs;
* dynamic document checklist;
* EMI, LTV, DTI and FOIR calculation;
* deterministic underwriting engine;
* detailed decision reasons and risk analysis;
* LangChain + Ollama integration;
* customer explanation generation;
* experimental officer summary generation;
* local Opik Docker tracing;
* maximum eligible loan estimation;
* loan amount affordability gap calculation;
* GitHub branch and pull-request tracking.

---

### Q65. What work has not started yet?

**Answer:**
The following features are not yet started:

* Phase 5 dedicated personalised recommendation node;
* automated unit-test suite;
* Streamlit or web UI;
* RAG-based policy Q&A;
* real document upload/verification;
* co-applicant support;
* scenario comparison;
* full deployment.

---

### Q66. Why was work paused before Phase 5?

**Answer:**
Work was paused before Phase 5 to:

* document everything already completed;
* make sure the current implementation is understood properly;
* prepare for the meeting;
* ask for feedback on project direction;
* confirm which feature should be prioritised next.

---

## Section 15: Questions to Ask in the Meeting

### Q67. What questions should I ask my senior about the current system?

**Answer:**
Ask:

1. Is the current home-loan journey flow aligned with the expected project scope?
2. Should the current underwriting rules remain prototype rules, or should they be based on a particular lending product or bank policy?
3. Is using local Ollama acceptable for the LLM layer?
4. Is local Opik tracing sufficient, or should evaluations and reports also be added?
5. Should the officer summary remain part of the project scope?

---

### Q68. What questions should I ask about future development?

**Answer:**
Ask:

1. Should I prioritise a personalised recommendation engine next?
2. Should I add automated tests before adding new features?
3. Should the next demo include a Streamlit user interface?
4. Is policy-based RAG expected in this project?
5. Should co-applicant support be added?
6. Should document upload and document verification be simulated or fully implemented?
7. Should a human loan-officer review step be added to the LangGraph workflow?
8. Should the project cover only initial assessment or the wider journey up to sanction and disbursement?

---

### Q69. What questions should I ask about demo and portfolio use?

**Answer:**
Ask:

1. Which test cases should be shown during the next demo?
2. May I save screenshots of the local Opik traces for documentation?
3. May I use a generic version of the architecture/project description in my portfolio or CV?
4. Are there any restrictions on pushing code or screenshots to GitHub?

---

## Section 16: Short Meeting Summary

### Q70. How can I explain the entire progress in a short answer?

**Answer:**
After the previous feedback, I upgraded the original basic home-loan checker into a more structured initial assessment workflow. It now takes customer, loan, property and document details; calculates EMI, LTV, DTI, FOIR and an estimated maximum eligible loan; applies a Python-based underwriting rule engine; and uses LangChain with local Ollama to generate customer and officer explanations. I also connected the workflow to a local Opik Docker setup so I can inspect node execution and LLM traces. I have completed development up to Phase 4 and paused before Phase 5 to document the work and confirm the next priority.

---

## Section 17: Planned Next Steps After Approval

### Q71. What is the proposed next phase?

**Answer:**
The proposed next phase is:

```text
Phase 5: Dedicated Personalised Recommendation Engine
```

This would generate clearer calculated guidance such as:

* reducing the requested loan amount by a specific value;
* explaining available EMI capacity;
* suggesting an increased down payment for high LTV;
* listing document and property-verification actions.

---

### Q72. What later phases can be considered?

**Answer:**

| Phase             | Feature                                    |
| ----------------- | ------------------------------------------ |
| Phase 5           | Personalised recommendation engine         |
| Phase 6           | Automated tests and final trace validation |
| Phase 7           | Streamlit user interface                   |
| Phase 8           | README, screenshots and demo preparation   |
| Advanced Phase 9  | Policy-based RAG Q&A                       |
| Advanced Phase 10 | Document upload and verification           |
| Advanced Phase 11 | Co-applicant and scenario comparison       |
| Advanced Phase 12 | Full deployment or frontend enhancement    |

---

## Final Note

The project is currently complete up to Phase 4. Phase 5 has not yet been started. The immediate goal is to explain the completed implementation, receive feedback on scope and priorities, and then continue development in the agreed direction.
