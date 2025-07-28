library(ellmer)

chat <- chat_anthropic(
  model = "claude-sonnet-4-20250514",
  system_prompt = "You are a presentation coach for data scientists.
  You give constructive, focused, and practical feedback on titles, structure, and storytelling.",
  params = params(
    temperature = 0.8 # default is 1
  )
)

# chat$chat(
#   "I'm working on a presentation with the title: 'The Shiny Side of LLMs'.
# Please evaluate the clarity, tone, and relevance of this title for the intended audience.
# For context, this is a 10-minute lightning talk at posit::conf(2025).
# The audience is Python and R users who are curious about AI and large language models,
# but not all of them have a deep technical background.
# The talk uses Shiny as a way to explore and demo LLMs in practice.
# Return your answer as a JSON array of objects, where each object has the following keys:
# - 'aspect': one of 'clarity', 'tone', or 'relevance'
# - 'feedback': your concise assessment
# - 'suggestion': an optional improvement if applicable"
# )

# Get Quarto presentation and convert to plain Markdown
quarto::quarto_render(
  "./Quarto/my-presentation.qmd",
  output_format = "markdown"
)

# Use prompt file
prompt_file <- "./prompts/prompt-analyse-slides-structured.md"

# Dynamic data
# Audience, length in minutes, type, and event
audience_content <- "Python and R users who are curious about AI and large language models, but not all of them have a deep technical background"
length_content <- "10"
type_content <- "lightning talk"
event_content <- "posit::conf(2025)"

# Read the generated Markdown file containing our slides
markdown_file <- "./Quarto/docs/my-presentation.md"
markdown_content <- readChar(markdown_file, file.size(markdown_file))

prompt_complete <- interpolate_file(
  path = prompt_file,
  audience = audience_content,
  length = length_content,
  type = type_content,
  event = event_content,
  markdown = markdown_content
)

# Type specification
type_suggested_improvements <- type_object(
  pacing = type_string(
    description = "Suggestions for improving pacing and structure: e.g. slides where pacing might be too fast or too slow based on the content density. Suggestions include slides that can be combined or split.",
    required = FALSE
  ),
  visual_design = type_string(
    description = "Suggestions for improving visual clarity or design: e.g. flag slides that are too text-heavy or cluttered. Includes recommendations for slide redesign like splitting text, adding visuals, or adding bullet points.",
    required = FALSE
  ),
  storytelling = type_string(
    description = "Suggestions for improving storytelling or logical flow: e.g. if the presentation can be improved by adding a motivating opening, summarizing key points before transitions, and a clear closure.",
    required = FALSE
  ),
  consistency = type_string(
    description = "Suggestions for improving consistency of style and structure: e.g. sudden shifts in slide formatting, tone, and visual elements that feel unintentional.",
    required = FALSE
  ),
  engagement = type_string(
    description = "Suggestions to make the presentation more engaging: e.g. if the presentation can be improved by adding interactive elements like questions, polls and demos, while keeping the time constraint in mind.",
    required = FALSE
  ),
  accessibility = type_string(
    description = "Suggestions for accessibility: e.g. slides with small text, poor color contrast, or a visual overload.",
    required = FALSE
  )
)

type_slide_analysis <- type_object(
  presentation_title = type_string(description = "The presentation title."),
  total_slides = type_integer(description = "Total number of slides."),
  percent_with_code = type_number(
    description = "Percentage of slides containing code blocks."
  ),
  percent_with_images = type_number(
    description = "Percentage of slides containing images."
  ),
  estimated_duration_minutes = type_integer(
    description = "Estimated presentation length in minutes, assuming ~1 minute per text slide and 2–3 minutes per code or image-heavy slide)."
  ),
  clarity_score = type_object(
    .description = "Clarity score and justification.",
    score = type_integer(description = "Score from 1 to 10."),
    justification = type_string(
      description = "Brief explanation justifying the score."
    )
  ),
  tone = type_string(
    description = "Brief description of the presentation tone (e.g., informal, technical, playful)."
  ),
  relevance_for_audience = type_object(
    .description = "Relevance for intended audience and concise explanation.",
    score = type_integer(description = "Score from 1 to 10."),
    justification = type_string(
      description = "Brief explanation justifying the score."
    )
  ),
  suggested_improvements = type_suggested_improvements
)

chat$chat_structured(prompt_complete, type = type_slide_analysis)

# Get tokens and costs for this script
chat$get_tokens()
chat$get_cost()
