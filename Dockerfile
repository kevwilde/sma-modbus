FROM python:3-alpine

ENV WORK_DIR=/smamodbus
ENV LOG_FILE=${WORK_DIR}/app.log
ENV SMA_HOST=""
ENV SMA_PORT=502
ENV MQTT_BROKER_HOST=localhost
ENV MQTT_BROKER_PORT=1883
ENV MQTT_PUBLISH_TOPIC="energy/solar/sma"
ENV CRON_SPEC="* * * * *" 

WORKDIR ${WORK_DIR}

COPY . ${WORK_DIR}
RUN pip install -r requirements.txt
RUN echo "${CRON_SPEC} python /smamodbus/smamodbus.py >> ${LOG_FILE} 2>&1" > ${WORK_DIR}/crontab
RUN touch ${LOG_FILE} # Needed for the tail
RUN crontab ${WORK_DIR}/crontab
RUN crontab -l
CMD crond  && tail -f ${LOG_FILE}
