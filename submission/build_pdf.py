"""Build the Week 9 submission PDF in rubric order.

AWS console images are optional. Drop them in submission/screenshots/ using the
names below and run this script again. Missing images leave a labeled box.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DEPLOY = ROOT / "deploy"
SHOTS = ROOT / "submission" / "screenshots"
OUT = ROOT / "submission" / "Week9_Deploy_AWS_OnPrem.pdf"

SCREENSHOTS = [
    ("01-iam-task-role.png", "IAM task role underwriting-risk-task-role. Show the trust relationship."),
    ("02-iam-task-policy.png", "Inline policy InvokeNovaLite. Both Bedrock ARNs must be readable."),
    ("03-iam-execution-role.png", "IAM execution role underwriting-risk-execution-role."),
    ("04-iam-execution-policy.png", "Inline policy PullRepoAndWriteLogs. Repository ARN and log group ARN readable."),
    ("05-build-push.png", "Terminal: docker build, docker tag, and docker push to ECR."),
    ("06-task-stopped.png", "ECS task stopped with container exit code 0."),
    ("07-cloudwatch-output.png", "CloudWatch log. deterministic_score 20 and deterministic_band low."),
    ("08-subnet.png", "Public subnet in the default VPC. Auto-assign public IPv4 is Yes."),
    ("09-security-group.png", "Security group underwriting-risk-sg. No inbound rules. Outbound TCP 443 only."),
]


class Submission(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "Week 9 risk agent  |  {0}".format(self.page_no()), align="C")
        self.set_text_color(0, 0, 0)


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    pdf = Submission(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(16, 16, 16)
    pdf.add_page()
    heading(pdf, "Week 9: Deploy a risk agent to AWS and a simulated on-prem host")
    body(
        pdf,
        "This PDF follows the lab order. Sections 1 through 6 are the evidence: "
        "IAM policies, the ECR push, the Fargate task, networking, the Ollama "
        "client, and the local run of case 900-01-0001. The written deployment "
        "document and the cost, complexity, and quality comparison follow. "
        "Console screenshots are inserted when the PNG files are present in "
        "submission/screenshots/. The click path is docs/CONSOLE.md.",
    )

    heading(pdf, "1. IAM role and attached policy")
    body(
        pdf,
        "Task role underwriting-risk-task-role is what the container uses. "
        "Execution role underwriting-risk-execution-role is what ECS uses to "
        "pull the image and write logs. Trust policy for both roles:",
    )
    code_block(pdf, (DEPLOY / "task-trust.json").read_text(encoding="utf-8"))
    body(pdf, "Task role inline policy. Replace REGION and ACCOUNT before saving it in the console.")
    code_block(pdf, (DEPLOY / "task-policy.json").read_text(encoding="utf-8"))
    body(pdf, "Execution role inline policy. Same REGION and ACCOUNT replacement.")
    code_block(pdf, (DEPLOY / "execution-policy.json").read_text(encoding="utf-8"))
    for name in SCREENSHOTS[:4]:
        shot(pdf, name[0], name[1])

    heading(pdf, "2. Build, push, and deploy")
    body(pdf, "From the repo root, after ECR shows View push commands. Replace ACCOUNT.")
    code_block(
        pdf,
        "\n".join(
            [
                "aws ecr get-login-password --region us-east-1 \\",
                "  | docker login --username AWS --password-stdin \\",
                "  ACCOUNT.dkr.ecr.us-east-1.amazonaws.com",
                "docker build -t underwriting-risk-agent .",
                "docker tag underwriting-risk-agent:latest \\",
                "  ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/underwriting-risk-agent:latest",
                "docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/underwriting-risk-agent:latest",
            ]
        ),
    )
    body(
        pdf,
        "Then ECS, task definition underwriting-risk-agent, Deploy, Run task "
        "(not Create service). Cluster underwriting-risk, the public subnet, "
        "security group underwriting-risk-sg, public IP turned on. The container "
        "has no port mapping. Environment: LLM_PROVIDER=bedrock, "
        "BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0, AWS_REGION=us-east-1. "
        "Task role and execution role are the two roles above.",
    )
    shot(pdf, SCREENSHOTS[4][0], SCREENSHOTS[4][1])

    heading(pdf, "3. AWS task output")
    body(
        pdf,
        "A correct CloudWatch log is one JSON object. deterministic_score is 20 "
        "and deterministic_band is low for Priya Shah. llm_score is an integer "
        "from 0 to 100. agreed is true when the model band is also low, and the "
        "kept score is the higher of the two. The task status is Stopped and "
        "the container exit code is 0.",
    )
    shot(pdf, SCREENSHOTS[5][0], SCREENSHOTS[5][1])
    shot(pdf, SCREENSHOTS[6][0], SCREENSHOTS[6][1])

    heading(pdf, "4. Networking")
    body(
        pdf,
        "Default VPC, one public subnet (auto-assign public IPv4 on), public IP "
        "on at Run task. Security group underwriting-risk-sg has no inbound rules. "
        "The only outbound rule is TCP 443 to 0.0.0.0/0. The task does not listen. "
        "The address is for outbound calls to ECR, CloudWatch Logs, and Bedrock. "
        "A private subnet would need a NAT gateway or interface endpoints, which "
        "this one-shot task does not use.",
    )
    shot(pdf, SCREENSHOTS[7][0], SCREENSHOTS[7][1])
    shot(pdf, SCREENSHOTS[8][0], SCREENSHOTS[8][1])

    heading(pdf, "5. Ollama setup and the local client")
    body(
        pdf,
        "Ollama is installed on this machine. The on-prem model is qwen3:8b "
        "(about 5.2 GB), with think set to false. The on-prem path does not call Bedrock. "
        "LLM_PROVIDER=ollama selects risk_agent/llm_ollama.py, which posts to "
        "http://127.0.0.1:11434/api/chat.",
    )
    code_block(pdf, (ROOT / "risk_agent" / "llm_ollama.py").read_text(encoding="utf-8"))

    heading(pdf, "6. Simulated on-prem output")
    body(
        pdf,
        "Command: LLM_PROVIDER=ollama OLLAMA_MODEL=qwen3:8b python3 -m risk_agent",
    )
    body(pdf, "Same fixture, fixtures/priya_shah.json. stdout:")
    code_block(pdf, (ROOT / "submission" / "onprem-output.json").read_text(encoding="utf-8"))
    body(
        pdf,
        "deterministic_score is 20 and deterministic_band is low. qwen3:8b "
        "with thinking off returned llm_score 15, also low, so agreed is true and the "
        "kept score is 20. The factors match the application. That 15 matches the "
        "Week 8 score for this applicant.",
    )

    heading(pdf, "7 and 8. Deployment document, comparison, and recommendation")
    render_markdown(pdf, (DOCS / "DEPLOYMENT.md").read_text(encoding="utf-8"))

    pdf.output(str(OUT))
    print(OUT)


def heading(pdf: FPDF, text: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def body(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 5.5, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def code_block(pdf: FPDF, text: str) -> None:
    pdf.set_font("Courier", "", 8)
    pdf.set_fill_color(244, 244, 244)
    for raw_line in text.splitlines() or [""]:
        line = raw_line if raw_line else " "
        chunks = [line[i : i + 92] for i in range(0, len(line), 92)] or [" "]
        for chunk in chunks:
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_font("Courier", "", 8)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 4, chunk, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)


def shot(pdf: FPDF, name: str, caption: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 5.5, caption, new_x="LMARGIN", new_y="NEXT")
    path = SHOTS / name
    if path.exists():
        pdf.ln(1)
        pdf.image(str(path), w=180)
        pdf.ln(2)
        return
    pdf.set_font("Helvetica", "I", 10)
    pdf.multi_cell(
        0,
        5,
        "Save this console screenshot as submission/screenshots/{0} and rerun python3 submission/build_pdf.py.".format(
            name
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    y = pdf.get_y() + 1
    if y > 230:
        pdf.add_page()
        y = pdf.get_y()
    pdf.set_draw_color(160, 160, 160)
    pdf.rect(16, y, 180, 28)
    pdf.set_xy(16, y + 10)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(180, 6, name, align="C")
    pdf.set_y(y + 32)


def render_markdown(pdf: FPDF, text: str) -> None:
    lines = text.splitlines()
    fence = False
    buffer = []
    for line in lines:
        if line.startswith("```"):
            if fence:
                code_block(pdf, "\n".join(buffer))
                buffer = []
                fence = False
            else:
                fence = True
            continue
        if fence:
            buffer.append(line)
            continue
        if line.startswith("# "):
            heading(pdf, line[2:].strip())
        elif line.startswith("## "):
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 6, line[3:].strip(), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif line.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 5.5, line[4:].strip(), new_x="LMARGIN", new_y="NEXT")
        elif line.startswith("- "):
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 5.5, "- " + line[2:].strip(), new_x="LMARGIN", new_y="NEXT")
        elif not line.strip():
            pdf.ln(1.5)
        else:
            body(pdf, line)


if __name__ == "__main__":
    main()
