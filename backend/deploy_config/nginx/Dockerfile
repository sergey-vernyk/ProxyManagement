FROM nginx:1.27-alpine

RUN mkdir -p /vol/web/static && \
    mkdir -p /vol/web/media && \
    mkdir -p /etc/nginx/includes

ARG user=nginx
ARG group=www-data

RUN addgroup $user $group

COPY ./modem_proxy.conf.template ./options-ssl-nginx.conf /etc/nginx/
COPY ./includes/ /etc/nginx/includes/

COPY ./run.sh /run.sh

RUN apk add --no-cache openssl bash vim curl && \
    chmod 775 /run.sh && \
    chmod 775 -R /etc/nginx/ && \
    chown -R $user:$group /vol && \
    chmod -R 755 /vol

EXPOSE 80/tcp
EXPOSE 443/tcp

CMD ["/run.sh"]