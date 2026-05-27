Please verify this potential finding by generating and executing a Proof-of-Concept (PoC).

# Finding Details
Title: {title}
Description: {description}
File Path: {file_path}
Vulnerable Code:
{vulnerable_code}

Project Tech Stack: {tech_stack}

# Your Task
1.  **Investigate**: Read the code and understand the vulnerability.
2.  **Generate PoC**: Create a script that demonstrates the flaw.
3.  **Execute**: Run the PoC in the isolated container.
4.  **Refine**: If the PoC fails (e.g., due to an error in the script, missing dependency, or unexpected environment state), analyze the failure logs, fix the PoC, and retry. Continue this refinement loop until you have a working PoC or you are certain the finding is a false positive.
5.  **Report**: Provide the final PoC code and the status (Verified, False Positive, or Unverified).

Return your final report in JSON format with fields: `status`, `poc`, and a brief `reasoning`.
