library(ellmer)

chat <- chat_anthropic(
  model = "claude-sonnet-4-20250514"
)

chat$chat(
  "I'm working on a presentation with the title: 'The Shiny Side of LLMs'. What's your feedback just based on that title?"
)
chat$chat("What is my presentation title?")
