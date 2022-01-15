FROM python:3.9
ADD ./requirements.txt .
RUN python3 -m pip install -r requirements.txt
RUN apt-get update && apt-get install fonts-liberation
ADD ./main.py .
RUN mkdir out
ENTRYPOINT ["./main.py"]
