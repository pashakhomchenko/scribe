# 🖋️ Scribe
Personal note-taker for conversations using Whisper and GPT

## Environmental files
This project depends on two .env files (one for backend and one for frontend) which you need to fill out yourself. There are .env.example files that will help you to find the right information

## Backend
We use Docker for development, so all you need to do is to make sure that you have Docker installed and run the following command:
`docker compose -f docker-compose.dev.yml up -d`

If you want to rebuild images then run the same command with `--build` argument:
`docker compose -f docker-compose.dev.yml up -d --build`

## Frontend
To install the frontend dependencies, go to the frontend directory and run the following command:
`npm install`

To launch the frontend, go to the frontend directory and run the following command:
`npm run dev`
