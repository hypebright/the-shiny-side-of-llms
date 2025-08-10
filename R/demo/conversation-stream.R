library(ellmer)

chat <- chat_anthropic(
  model = "claude-sonnet-4-20250514",
  system_prompt = "You are a presentation coach for data scientists.
  You give constructive, focused, and practical feedback on titles, structure, and storytelling.",
  params = params(
    temperature = 0.8 # default is 1
  )
)

stream <- chat$stream(
  "I'm working on a presentation with the title: 'The Shiny Side of LLMs'.
Please evaluate the clarity, tone, and relevance of this title for the intended audience.
For context, this is a 10-minute lightning talk at posit::conf(2025).
The audience is Python and R users who are curious about AI and large language models,
but not all of them have a deep technical background.
The talk uses Shiny as a way to explore and demo LLMs in practice.
Return your answer as a JSON array of objects, where each object has the following keys:
- 'aspect': one of 'clarity', 'tone', or 'relevance'
- 'feedback': your concise assessment
- 'suggestion': an optional improvement if applicable"
)

coro::loop(
  for (chunk in stream) {
    cat(chunk)
  }
)
