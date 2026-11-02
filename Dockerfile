FROM python:3.14-slim

WORKDIR /code

# Install Python dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copy app code
COPY . .
RUN mkdir -p /code/data && chmod 777 /code/data

# Pass the key at runtime: docker run --env-file .env -p 7860:7860 codesynapse
CMD ["python", "app.py"]
