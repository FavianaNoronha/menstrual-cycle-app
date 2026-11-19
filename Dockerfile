FROM python:3.12-slim
WORKDIR /srv
COPY packages/cycle_engine packages/cycle_engine
COPY services/api services/api
RUN pip install --no-cache-dir ./packages/cycle_engine ./services/api
ENV DATABASE_PATH=/data/companion.db
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
