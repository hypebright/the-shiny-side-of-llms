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

# Get Quarto presentation and convert to plain Markdown + HTML
quarto::quarto_render(
  "./Quarto/my-presentation.qmd",
  output_format = c("markdown", "html")
)

# Use prompt file
# Step 1: first step of the analysis (meta-data)
prompt_file_1 <- "./prompts/prompt-analyse-slides-structured-tool-1.md"
# Step 2: second step of the analysis (detailed analysis with improvements)
prompt_file_2 <- "./prompts/prompt-analyse-slides-structured-tool-2.md"

# Dynamic data
# Audience, length in minutes, type, and event
audience_content <- "Python and R users who are curious about AI and large language models, but not all of them have a deep technical background"
length_content <- "10"
type_content <- "lightning talk"
event_content <- "posit::conf(2025)"

# Read the generated Markdown file containing our slides
markdown_file <- "./Quarto/docs/my-presentation.md"
markdown_content <- readChar(markdown_file, file.size(markdown_file))
html_file <- "./Quarto/docs/my-presentation.html"

# Construct the first prompt
prompt_complete_1 <- interpolate_file(
  path = prompt_file_1,
  audience = audience_content,
  length = length_content,
  type = type_content,
  event = event_content,
  html_file_path = html_file,
  markdown = markdown_content
)

# Read the second prompt (no dynamic data)
prompt_complete_2 <- readChar(prompt_file_2, file.size(prompt_file_2))

#chat$chat(prompt_complete_1)

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
  concistency = type_array(
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
#' @param html_file Path to the HTML file generated by Quarto.
#' @param metric The metric to calculate: "total_slides" for total number of slides,
#' "code" for percentage of slides containing fenced code blocks, or "images"
#' for percentage of slides containing images.
#' @return The calculated metric value.
calculate_slide_metric <- function(html_file, metric) {
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
  html_file = type_string(
    "Path to the HTML file generated by Quarto",
    required = TRUE
  ),
  metric = type_string(
    'The metric to calculate: "total_slides" for total number of slides, 
      "code" for percentage of slides containing fenced code blocks, or "images"
      for percentage of slides containing images.',
    required = TRUE
  )
)

chat$register_tool(calculate_slide_metric)

# Step 1: use regular chat to extract meta-data
# Note that this *should* make use of our tool
chat$chat(prompt_complete_1)

# Step 2: use structured chat to further analyse the slides
chat$chat_structured(prompt_complete_2, type = type_deck_analysis)

# Get tokens and costs for this script
chat$get_tokens()
chat$get_cost()
