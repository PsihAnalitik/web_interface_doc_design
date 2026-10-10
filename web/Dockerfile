FROM node:22.13-alpine

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=4173

WORKDIR /app/web
COPY --chown=node:node web/server.mjs web/events.mjs ./
COPY --chown=node:node web/dist ./dist
COPY --chown=node:node docs/document_design.md /app/docs/document_design.md
RUN mkdir -p /app/data && chown node:node /app/data

ENV QUESTION_EVENTS_DB=/app/data/question-events.sqlite

USER node
EXPOSE 4173
CMD ["node", "server.mjs"]
