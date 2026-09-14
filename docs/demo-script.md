# Two-minute recording script

Use a configured terminal for Azure, but keep the terminal and credentials off-screen.

## 0:00–0:12 — Introduce the product

Open the scripted replay page.

Say:

> Agent Flight Recorder evaluates observable AI tool actions before execution. It tracks the session and the data behind each action without requesting private model reasoning.

## 0:12–0:25 — Show the live Azure boundary

Open **Live Azure** and choose **Safe internal report**. Click **Run live Azure**.

Say:

> Azure OpenAI proposes the next action. Trusted application code supplies the security labels. The deterministic recorder and execution gate make the final decision.

## 0:25–0:55 — Approve real model proposals

Let the document read execute. When the restricted query pauses, click **Approve and execute**. Approve the export if it pauses.

Say:

> The document read executes. Restricted access requires human review. An approval is bound to this one action, and the tool result becomes context for the next model proposal.

Wait for **Model stopped**.

## 0:55–1:20 — Show the trace

Click **Download session trace**.

Say:

> The trace records the proposal, score, reasons, approval outcome, data links, and execution result. It excludes the API key and private reasoning.

## 1:20–1:52 — Show deterministic provenance replay

Return to **Scripted replay**. Select **Artifact provenance** and click **Run scenario**.

Say:

> This offline replay isolates artifact policy. Two exports share one session but have different sources. The public export is allowed to upload. The restricted export is blocked because its source records remain Restricted.

Show the provenance table first.

## 1:52–2:00 — Close on the enforcement point

Say:

> AI proposes. Humans review when required. Deterministic policy controls execution before a sensitive tool action can run.

## Recording rules

- Keep **Live Azure** and **Scripted replay** labels visible.
- Do not call the scripted replay a live AI attack.
- Do not claim the live model proposed an upload unless it actually did.
- If the model stops after the export, describe that as **model stopped**.
- If a Review action is rejected, describe it as **human rejection**.
- Use the scripted provenance replay to show the Block result.
- Leave the API key and PowerShell window outside the recording frame.
