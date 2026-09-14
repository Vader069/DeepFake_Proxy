# DeepFake Proxy Project 
What will this application achieve?
- Used for fake profile pic submissions on crucial websites.
- Identifies the AI generated submissions based on image classifications
## How does it work?
Instead of checking for viruses (which is standard), it analyzes the pixels and metadata for synthetic anomalies—like the unnatural blending of a face, strange lighting artifacts, or AI-generated noise. If it detects a deepfake, it immediately quarantines the file and alerts the system administrators. If the file is legitimate, it passes it through to the public-facing application.
## WorkFlow of the Task
To make this as an enterprise-grade project, we won't just use a simple server. We will build an automated, serverless pipeline.

1. The Drop-Off (Amazon S3 & Presigned URLs)
A user attempts to upload a video or image via a simple frontend web page.
Instead of pushing heavy video files through an API Gateway (which has a 10MB limit and would cause your architecture to fail a stress test), your frontend requests a secure, temporary "Presigned URL" from a lightweight AWS Lambda function.
The user's browser uploads the file directly to an Amazon S3 "Ingestion Bucket".

2. The Tripwire (S3 Event Notifications)

The moment the file completely lands in the Ingestion Bucket, it triggers an automatic AWS event. It acts as an invisible tripwire that instantly wakes up the next part of the system without requiring a server to sit around waiting.

3. The Interrogation (AWS Lambda Compute)
The tripwire triggers a "Processing" AWS Lambda function.
This Lambda function takes the file and Processes it using the built in serverless compute service running a lightweight EfficientNet-B0 model.

4. The Verdict (DynamoDB & SNS Orchestration)
Based on that score, the Lambda function executes the final judgment:
If it's a Deepfake: The file is immediately moved to an S3 "Quarantine Bucket" and deleted from the Ingestion Bucket. An Amazon SNS (Simple Notification Service) topic fires an email alert to the security team letting them know a synthetic upload was attempted.
If it's Real: The file is moved to an S3 "Production Bucket" where the main application can safely use it.

In both cases, a log of the transaction (timestamp, file name, AI score) is written to an Amazon DynamoDB table for auditing.

## AWS configurations:
> Initially creating a free tier account on AWS and note that only one account can be created per email and that email is permanently blocked by AWS even after account termination.

==Creating an IAM user==
1. Go to AWS console for root/admin
2. select users>create user
3. Enter the username and a default autogen password or a custom password for the user
4. Then setup the permissions that are to be granted to that user in "Attach policies directly" and select "AdministratorAccess" if the user wants almost root like privillages.
5. Then select create user button which creates the new user with its custom account id and password and download it as CSV file to send it securely to the user.

