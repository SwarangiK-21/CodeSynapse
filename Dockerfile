FROM python:3.14-slim

WORKDIR /code

# Install Python dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copy app code
COPY . .

# Pass settings at runtime: docker run --env-file .env -p 7860:7860 codesynapse
# Set DATABASE_URL to Postgres; the default SQLite file is lost with the container
CMD ["python", "app.py"]
