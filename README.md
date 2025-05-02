##Rubri-Backend

### Main user: Interviewer

### What Function:
This tool assists interviewers by generating an evaluation rubric based on the Job Description (JD) and the candidate's resume. This allows for a comprehensive and structured assessment of the candidate against the required criteria. The application enables interviewers to conduct evaluations effectively, providing a consistent framework for assessing candidates holistically based on the defined requirements.

###  High-Level Functional Requirements (FRs):

### Key Requirements:

1. Rubric Generation and Usage:

    Generate an evaluation rubric based on a provided Job Description (JD) and candidate resume.
    The rubric must be fillable by the interviewer during the interview.
    Allow editing of the completed rubric after the interview.
    Include functionality to export the final evaluation rubric to a PDF document.
        1.1 Rubric Modification: Enable users to modify the evaluation rubric template (potentially involving discussion/interaction, e.g., with an LLM or based on feedback).

2. Rubric Template History: Maintain a historical record of all previously generated evaluation rubric templates, accessible to the user.

### Possible APIs

#### Upload Ops
/upload/file/jd Support PDFs,Text,Word
/upload/file/resume Support PDFs, Text, Word
/upload/text/jd
/upload/text/resume

#### Rubric ops
/rubric/create  - To create initial rubric based on JD OR Resume OR Both
/rubric/chat - To Chat with llm and update the rubric
/rubric/edit - To edit the generated rubric by user directly
/rubric/export/link - To export the genrated rubric as link
/rubric/export/pdf - To export the genrated rubric as pdf
/rubric/list - To list the generated rubric uptill now