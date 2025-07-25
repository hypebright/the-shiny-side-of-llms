from chatlas import ChatAnthropic, interpolate_file
import subprocess
from pathlib import Path

chat = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    system_prompt="You are a presentation coach for data scientists. You give constructive, focused, and practical feedback on titles, structure, and storytelling.",
)

# chat.chat(
#     """I'm working on a presentation with the title: 'The Shiny Side of LLMs'.
#         Please evaluate the clarity, tone, and relevance of this title for the intended audience.
#         For context, this is a 10-minute lightning talk at posit::conf(2025).
#         The audience is Python and R users who are curious about AI and large language models,
#         but not all of them have a deep technical background.
#         The talk uses Shiny as a way to explore and demo LLMs in practice.
#         Return your answer as a JSON array of objects, where each object has the following keys:
#         - 'aspect': one of 'clarity', 'tone', or 'relevance'
#         - 'feedback': your concise assessment
#         - 'suggestion': an optional improvement if applicable"""
# )

# Get Quarto presentation and convert to plain Markdown
subprocess.run(["quarto", "render", "./Quarto/my-presentation.qmd", "--to", "markdown"])

# Use prompt file
prompt_file = "./prompts/prompt-analyse-slides.md"

# Dynamic data
# Audience, length in minutes, type, and event
audience_content = "Python and R users who are curious about AI and large language models, but not all of them have a deep technical background"
length_content = "10"
type_content = "lightning talk"
event_content = "posit::conf(2025)"

# Read the generated Markdown file containing our slides
markdown_file = Path("./Quarto/docs/my-presentation.md")
markdown_content = markdown_file.read_text(encoding="utf-8")

prompt_complete = interpolate_file(
    prompt_file,
    variables={
        "audience": audience_content,
        "length": length_content,
        "type": type_content,
        "event": event_content,
        "markdown": markdown_content,
    },
)

chat.chat(prompt_complete)

# Get tokens for this script
chat.get_tokens()
