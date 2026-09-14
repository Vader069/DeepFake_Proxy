# 1. Pull the official AWS Lambda Python 3.12 base image
FROM public.ecr.aws/lambda/python:3.12

# 2. Copy your requirements file into the container
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# 3. Install the dependencies inside the container
RUN pip install -r requirements.txt

# 4. Copy your brain and your execution script into the container
COPY model.onnx ${LAMBDA_TASK_ROOT}
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# 5. Tell AWS exactly which script and function to trigger when an image arrives
CMD [ "lambda_function.lambda_handler" ]