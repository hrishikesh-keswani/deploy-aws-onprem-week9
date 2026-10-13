# Console runbook: risk agent on ECS Fargate

Region for every step: **us-east-1**. The task runs once and exits. Do not create an ECS service.

Your console user is only the deployer. The running container uses `underwriting-risk-task-role`. ECS uses `underwriting-risk-execution-role` to pull the image and write logs.

Before the IAM policies, replace `REGION` with `us-east-1` and `ACCOUNT` with your 12-digit account id (account menu, top right of the console).

## 1. Bedrock model

1. Open the Amazon Bedrock console in us-east-1.
2. If you see **Model access**, enable **Amazon Nova Lite** (`amazon.nova-lite-v1:0`) and wait until it says Access granted.
3. If that page is gone, Nova Lite is already invokable. Keep the model id `us.amazon.nova-lite-v1:0`.
4. If Nova Lite is blocked, enable one other on-demand text model and change `BEDROCK_MODEL_ID` in the task definition and both resource ARNs in `deploy/task-policy.json` to that model. Do not change only one of them.

## 2. IAM task role

This is the identity the agent code uses. It can call one model and nothing else.

1. IAM, **Roles**, **Create role**.
2. Trusted entity type: **AWS service**.
3. Use case: **Elastic Container Service**, then **Elastic Container Service Task**. Next.
4. Do not attach a managed policy. Next.
5. Role name: `underwriting-risk-task-role`. Create role.
6. Open the role. **Trust relationships** should match `deploy/task-trust.json` (`ecs-tasks.amazonaws.com` may call `sts:AssumeRole`).
7. **Add permissions**, **Create inline policy**, **JSON**. Paste `deploy/task-policy.json` after replacing `REGION` and `ACCOUNT`. Policy name: `InvokeNovaLite`.
8. Screenshots, saved under `submission/screenshots/`:
   - `01-iam-task-role.png` - role summary, trust relationship visible.
   - `02-iam-task-policy.png` - the JSON policy, both ARNs readable.

## 3. IAM execution role

This role never calls the model. It only pulls this repository and writes this log group.

1. Create another role the same way (Elastic Container Service Task).
2. Role name: `underwriting-risk-execution-role`.
3. Inline policy from `deploy/execution-policy.json`, same `REGION` and `ACCOUNT` replacement. Policy name: `PullRepoAndWriteLogs`.
4. Screenshots:
   - `03-iam-execution-role.png` - role summary.
   - `04-iam-execution-policy.png` - the JSON, repository ARN and log group ARN readable.

`ecr:GetAuthorizationToken` stays on `*`. That action does not accept a repository ARN.

## 4. CloudWatch log group

1. CloudWatch, **Log groups**, **Create log group**.
2. Name: `/ecs/underwriting-risk-agent`.
3. Retention: 1 day. Create.

The execution role cannot create the group. This step has to happen first.

## 5. ECR repository and push

1. ECR, **Create repository**.
2. Visibility: Private. Name: `underwriting-risk-agent`. Tag mutability: Mutable. Scan on push: off. Create.
3. Open the repository, **View push commands**. Those four commands are the only terminal steps.
4. Install the AWS CLI v2 if `aws` is missing: the macOS installer at `https://awscli.amazonaws.com/AWSCLIV2.pkg`. Then `aws configure` with an access key from IAM, **Security credentials**, **Create access key** (use case: Command Line Interface). This key is for the push only. It is not inside the container.
5. Start Docker Desktop. From this repo:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker build -t underwriting-risk-agent .
docker tag underwriting-risk-agent:latest ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/underwriting-risk-agent:latest
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/underwriting-risk-agent:latest
```

6. Screenshot `05-build-push.png` - the terminal from `docker build` through a finished `docker push`.

## 6. Networking

The task does not listen for connections. It needs outbound HTTPS so Fargate can pull the image and the process can call Bedrock.

1. VPC, **Your VPCs**. Note the **default** VPC id.
2. VPC, **Subnets**. Pick one subnet in that VPC whose **Auto-assign public IPv4 address** is Yes. Note the subnet id. Screenshot `08-subnet.png` with the subnet id, the VPC, and Auto-assign public IPv4.
3. Optional check: **Route tables**, the subnet's main route should include `0.0.0.0/0` to an `igw-`. That is what makes the subnet public.
4. EC2, **Security groups**, **Create security group**.
   - Name: `underwriting-risk-sg`
   - VPC: the default VPC
   - Inbound rules: none. Remove a rule if the form adds one.
   - Outbound rules: delete the default allow-all rule. Add one rule: Type HTTPS, Protocol TCP, Port 443, Destination `0.0.0.0/0`.
5. Screenshot `09-security-group.png` - inbound empty, outbound only 443.

A private subnet would also be valid, and it would need a NAT gateway or interface endpoints for ECR, S3, CloudWatch Logs, and Bedrock. Those cost money every hour. This task has no inbound traffic, so a public subnet with a public IP and a closed inbound list is the smaller setup. The public IP is only for outbound calls.

## 7. ECS task definition and run

1. ECS, **Clusters**, **Create cluster**. Name: `underwriting-risk`. Infrastructure: AWS Fargate only. Do not create a new VPC. Create.
2. ECS, **Task definitions**, **Create new task definition**.
   - Family: `underwriting-risk-agent`
   - Launch type: AWS Fargate
   - Operating system / architecture: Linux / X86_64
   - CPU: .25 vCPU. Memory: .5 GB
   - Task role: `underwriting-risk-task-role`
   - Task execution role: `underwriting-risk-execution-role`
   - Container name: `risk-agent`
   - Image URI: `ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/underwriting-risk-agent:latest`
   - Port mappings: none
   - Environment:
     - `LLM_PROVIDER` = `bedrock`
     - `BEDROCK_MODEL_ID` = `us.amazon.nova-lite-v1:0`
     - `AWS_REGION` = `us-east-1`
   - Logging: Use log collection. Log group `/ecs/underwriting-risk-agent`, region us-east-1, stream prefix `ecs`.
3. Create.
4. Open the task definition, **Deploy**, **Run task**. Not **Create service**.
   - Cluster: `underwriting-risk`
   - Launch type: Fargate
   - VPC: default
   - Subnet: the public subnet from step 6
   - Security group: `underwriting-risk-sg`
   - Public IP: **Turned on**
5. Wait until **Last status** is Stopped and the container exit code is 0. Screenshot `06-task-stopped.png`.
6. Open the task, **Logs** (or CloudWatch, the log group, the newest stream). Screenshot `07-cloudwatch-output.png` so the JSON is readable. `deterministic_score` must be `20` and `deterministic_band` must be `low`.

A stopped task is not billed further. Do not leave a service desired-count above zero.

## 8. Rebuild the PDF after the screenshots

Put the nine PNGs in `submission/screenshots/` using the names above, then:

```bash
python3 submission/build_pdf.py
```

The PDF is `submission/Week9_Deploy_AWS_OnPrem.pdf`.
