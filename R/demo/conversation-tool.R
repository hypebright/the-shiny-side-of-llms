library(ellmer)

# Get Quarto presentation and convert to plain Markdown + HTML
quarto::quarto_render(
  "./Quarto/my-presentation.qmd",
  output_format = c("markdown", "html")
)

# Dynamic data
# Audience, length in minutes, type, and event
audience_content <- "Python and R users who are curious about AI and large language models, but not all of them have a deep technical background"
length_content <- "10"
type_content <- "lightning talk"
event_content <- "posit::conf(2025)"

# Read the generated Markdown file containing our slides
markdown_file <- "./Quarto/docs/my-presentation.md"
markdown_content <- readChar(markdown_file, file.size(markdown_file))

# Define prompt file
system_prompt_file <- "./prompts/prompt-analyse-slides-structured-tool.md"

# Create system prompt
system_prompt <- interpolate_file(
  path = system_prompt_file,
  audience = audience_content,
  length = length_content,
  type = type_content,
  event = event_content
)

# Reusable scoring category
type_scoring_category <- type_object(
  score = type_integer(
    description = "Score from 1 to 10."
  ),
  justification = type_string(
    description = "Brief explanation of the score."
  ),
  improvements = type_string(
    description = "Concise, actionable improvements, mentioning slide numbers if applicable.",
    required = FALSE
  ),
  score_after_improvements = type_integer(
    description = "Estimated score after suggested improvements."
  )
)

# Top-level deck analysis object
type_deck_analysis <- type_object(
  presentation_title = type_string(description = "The presentation title."),
  total_slides = type_integer(description = "Total number of slides."),
  percent_with_code = type_number(
    description = "Percentage of slides containing code blocks (0–100)."
  ),
  percent_with_images = type_number(
    description = "Percentage of slides containing images (0–100)."
  ),
  estimated_duration_minutes = type_integer(
    description = "Estimated presentation length in minutes, assuming ~1 minute per text slide and 2–3 minutes per code or image-heavy slide."
  ),
  tone = type_string(
    description = "Brief description of the presentation tone (e.g., informal, technical, playful)."
  ),
  clarity = type_array(
    description = "Evaluate how clearly the ideas are communicated. Are the explanations easy to understand? Are terms defined when needed? Is the key message clear?",
    type_scoring_category
  ),
  relevance = type_array(
    description = "Asses how well the content matches the audience’s background, needs, and expectations. Are examples, depth of detail, and terminology appropriate for the audience type?",
    type_scoring_category
  ),
  visual_design = type_array(
    description = "Judge the visual effectiveness of the slides. Are they readable, visually balanced, and not overcrowded with text or visuals? Is layout used consistently?",
    type_scoring_category
  ),
  engagement = type_array(
    description = "Estimate how likely the presentation is to keep attention. Are there moments of interactivity, storytelling, humor, or visual interest that invite focus?",
    type_scoring_category
  ),
  pacing = type_array(
    description = "Analyze the distribution of content across slides. Are some slides too dense or too light? ",
    type_scoring_category
  ),
  structure = type_array(
    description = "Review the logical flow of the presentation. Is there a clear beginning, middle, and end? Are transitions between topics smooth? Does the presentation build toward a conclusion?",
    type_scoring_category
  ),
  consistency = type_array(
    description = "Evaluate whether the presentation is consistent when it comes to formatting, tone, and visual elements. Are there any elements that feel out of place?",
    type_scoring_category
  ),
  accessibility = type_array(
    description = "Consider how accessible the presentation would be for all viewers, including those with visual or cognitive challenges. Are font sizes readable? Is there sufficient contrast? Are visual elements not overwhelming?",
    type_scoring_category
  )
)

# Define a tool to calculate some metrics
# Start with a function:

#' Calculates the total number of slides, percentage of slides with code blocks,
#' and percentage of slides with images in a Quarto presentation HTML file.
#'
#' @param metric The metric to calculate: "total_slides" for total number of slides,
#' "code" for percentage of slides containing fenced code blocks, or "images"
#' for percentage of slides containing images.
#' @return The calculated metric value.
calculate_slide_metric <- function(metric) {
  html_file <- "./Quarto/docs/my-presentation.html"
  if (!file.exists(html_file)) {
    stop(
      "HTML file does not exist. Please render your Quarto presentation first."
    )
  }
  # Read HTML file
  html_content <- readChar(html_file, file.size(html_file))

  # Split on <section> tags to get individual slides
  slides <- unlist(strsplit(html_content, "<section"))

  total_slides <- length(slides)

  if (metric == "total_slides") {
    result <- total_slides
  } else if (metric == "code") {
    # Count slides where we see the "sourceCode" class
    slides_with_code <- sum(grepl('class="sourceCode"', slides))
    result <- round((slides_with_code / total_slides) * 100, 2)
  } else if (metric == "images") {
    # Count slides with image tag
    slides_with_image <- sum(grepl('<img', slides))
    result <- round((slides_with_image / total_slides) * 100, 2)
  } else {
    stop("Unknown metric: choose 'total_slides', 'code', or 'images'")
  }

  return(result)
}

# Optionally, to avoid manual work:
# create_tool_def(calculate_slide_metric)
calculate_slide_metric <- tool(
  calculate_slide_metric,
  "Returns the calculated metric value",
  metric = type_string(
    'The metric to calculate: "total_slides" for total number of slides, 
      "code" for percentage of slides containing fenced code blocks, or "images"
      for percentage of slides containing images.',
    required = TRUE
  )
)

# Initialise chat with Claude Sonnet 4 model
chat <- chat_anthropic(
  model = "claude-sonnet-4-20250514",
  system_prompt = system_prompt,
  params = params(
    temperature = 0.8 # default is 1
  )
)

# Register the tool with the chat
chat$register_tool(calculate_slide_metric)

# Start conversation with the chat
# Task 1: regular chat to extract meta-data
chat$chat(
  interpolate(
    "Execute Task 1 (counts). Here are the slides in Markdown: {{ markdown_content }}"
  )
)

# Task 2: structured chat to further analyse the slides
chat$chat_structured(
  "Execute Task 2 (suggestions)",
  type = type_deck_analysis
)

# Get tokens and costs for this script
chat$get_tokens()
chat$get_cost()
