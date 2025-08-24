library(shiny)
library(bslib)
library(ellmer)
library(ggplot2)
library(ggiraph)
library(gdtools)
library(purrr)
library(dplyr)

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
#' @param metric The metric to calculate: "total_slides" for total number of slides,
#' "code" for percentage of slides containing fenced code blocks, or "images"
#' for percentage of slides containing images.
#' @return The calculated metric value.
calculate_slide_metric <- function(metric) {
  html_file <- paste0(tempdir(), "/my-presentation.html")
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

# Register Monteserrat font
register_gfont("Lato")

ui <- page_fillable(
  ## Options
  ## Busy indication is enabled by default for UI created with bslib (which we use here),
  ## but must be enabled otherwise with useBusyIndicators().
  ## useBusyIndicators(),
  ## General theme and styles
  ## 1. Bootswatch theme
  theme = bs_theme(bootswatch = "flatly"),
  ## 2. Custom CSS
  tags$style(HTML(
    "
    #suggested_improvements table {
      font-family: 'Lato', sans-serif;
      font-size: 16px;
    }
  "
  )),
  ## Layout
  layout_sidebar(
    ## Sidebar content
    sidebar = sidebar(
      width = 400,
      # Open sidebar on mobile devices and show above content
      open = list(mobile = "always-above"),
      strong(p("Hey, I am DeckCheck!")),
      p(
        "I can help you improve your Quarto presentations by analysing them and suggesting improvements.
      Before I can do that, I need some information about your presentation."
      ),
      fileInput(
        inputId = "file",
        label = "Upload your Quarto presentation",
        accept = c(".qmd", ".qmdx")
      ),
      textAreaInput(
        inputId = "audience",
        height = "150px",
        label = "Describe your audience",
        placeholder = "e.g. Python and R users who are curious about AI and large language models, but not all of them have a deep technical background"
      ),
      numericInput(
        inputId = "length",
        label = "Time cap for the presentation (minutes)",
        value = 10
      ),
      textInput(
        inputId = "type",
        label = "Type of talk",
        placeholder = "e.g. lightning talk, workshop, or keynote"
      ),
      textInput(
        inputId = "event",
        label = "Event name",
        placeholder = "e.g. posit::conf(2025)"
      ),
      input_task_button(
        id = "submit",
        label = shiny::tagList(
          bsicons::bs_icon("robot"),
          "Analyse presentation"
        ),
        label_busy = "DeckCheck is checking...",
        type = "default"
      )
    ),
    ## Main content
    layout_column_wrap(
      fill = FALSE,
      ### Value boxes for metrics
      value_box(
        title = tooltip(
          span(
            "Showtime ",
            bsicons::bs_icon("question-circle-fill")
          ),
          "Slides are being counted based on the provided Quarto presentation, then an educated guess is made about the time it will take to present them."
        ),
        value = textOutput("showtime"),
        showcase = bsicons::bs_icon("file-slides"),
        theme = "primary"
      ),
      value_box(
        title = tooltip(
          span(
            "Code Savviness ",
            bsicons::bs_icon("question-circle-fill")
          ),
          "Code Saviness is calculated based on the slides that contain code chunks. The percentage is the ratio of those slides to total slides."
        ),
        value = textOutput("code_savviness"),
        showcase = bsicons::bs_icon("file-code"),
        theme = "primary"
      ),
      value_box(
        title = tooltip(
          span(
            "Image Presence ",
            bsicons::bs_icon("question-circle-fill")
          ),
          "Image Presence is calculated based on the slides that contain images. The percentage is the ratio of those slides to total slides."
        ),
        value = textOutput("image_presence"),
        showcase = bsicons::bs_icon("file-image"),
        theme = "primary"
      )
    ),
    layout_column_wrap(
      fill = FALSE,
      width = 1 / 2,
      ### Graph with scoring metrics
      card(
        height = 600,
        card_header(
          strong("Scores per category")
        ),
        girafeOutput(
          outputId = "scores"
        )
      ),
      ### Table with suggested improvements
      card(
        height = 600,
        card_header(strong("Suggested improvements per category")),
        tableOutput(
          outputId = "suggested_improvements"
        )
      )
    ),
    ### Feedback buttons
    fluidRow(
      class = "d-flex p-2 gap-2",
      actionButton(
        inputId = "like",
        label = shiny::tagList(
          bsicons::bs_icon("hand-thumbs-up"),
          "Like"
        ),
        class = "btn-success btn-sm opacity-75",
        width = "100px"
      ),
      actionButton(
        inputId = "dislike",
        label = shiny::tagList(
          bsicons::bs_icon("hand-thumbs-down"),
          "Dislike"
        ),
        # small button
        class = "btn-danger btn-sm opacity-75",
        width = "100px"
      )
    )
  )
)

server <- function(input, output, session) {
  chat_task <- ExtendedTask$new(function(
    system_prompt,
    markdown_content,
    type_deck_analysis
  ) {
    # We're using an Extended Task to avoid blocking the and
    # we start a fresh chat session each time.
    # For a feedback loop, we would use a persistent chat session.
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
    chat_res <- chat$chat_async(
      interpolate(
        "Execute Task 1 (counts). Here are the slides in Markdown: {{ markdown_content }}"
      )
    )

    chat_res$then(function(res) {
      # Print the response from Task 1
      cat("Response from Task 1:\n")
      cat(res, "\n\n")

      # Execute next task
      # Task 2: structured chat to further analyse the slides
      chat$chat_structured_async(
        "Execute Task 2 (suggestions)",
        type = type_deck_analysis
      )
    })
  }) |>
    bind_task_button("submit")

  observe({
    req(input$file)
    req(input$audience)
    req(input$length)
    req(input$type)
    req(input$event)

    # Get file path of the uploaded file
    file_path <- input$file$datapath

    # Move to temp dir and give consistent name
    file.copy(
      file_path,
      paste0(tempdir(), "/my-presentation.qmd"),
      overwrite = TRUE
    )

    # Get Quarto presentation and convert to plain Markdown + HTML
    quarto::quarto_render(
      input = paste0(tempdir(), "/my-presentation.qmd"),
      output_format = c("markdown", "html")
    )

    # Markdown file is generated in the same directory as the input file
    markdown_file <- paste0(tempdir(), "/my-presentation.md")

    # Read the generated Markdown file containing our slides
    markdown_content <- readChar(markdown_file, file.size(markdown_file))

    # Define prompt file
    system_prompt_file <- "../../prompts/prompt-analyse-slides-structured-tool.md"

    # Create system prompt
    system_prompt <- interpolate_file(
      path = system_prompt_file,
      audience = input$audience,
      length = input$length,
      type = input$type,
      event = input$event
    )

    # Trigger the chat task with the provided inputs
    chat_task$invoke(
      system_prompt = system_prompt,
      markdown_content = markdown_content,
      type_deck_analysis = type_deck_analysis
    )
  }) |>
    bindEvent(input$submit)

  # Reactive expression to hold the analysis result
  analysis_result <- reactive({
    named_list <- chat_task$result()

    meta <- tibble(
      presentation_title = named_list$presentation_title,
      total_slides = named_list$total_slides,
      percent_with_code = named_list$percent_with_code,
      percent_with_images = named_list$percent_with_images,
      estimated_duration_minutes = named_list$estimated_duration_minutes,
      tone = named_list$tone
    )

    # evaluation sections (clarity, relevance, etc.)
    eval_sections <- c(
      "clarity",
      "relevance",
      "visual_design",
      "engagement",
      "pacing",
      "structure",
      "concistency",
      "accessibility"
    )

    evals <- map_dfr(eval_sections, function(section) {
      as_tibble(named_list[[section]][[1]]) %>%
        mutate(
          category = section,
          .before = 1
        )
    })

    # final tidy data frame
    final <- list(
      meta = meta,
      evals = evals
    )
  })

  output$scores <- renderGirafe({
    req(analysis_result())

    evals <- analysis_result()$evals

    # order by score
    data <- evals |>
      arrange(score) |>
      mutate(
        category = factor(category, levels = category),
        tooltip = paste0(
          "Score: ",
          score,
          "\n",
          "After improvements: ",
          score_after_improvements,
          "\n",
          "Justification: ",
          justification
        )
      ) |>
      select(category, score, score_after_improvements, tooltip)

    # set fill to
    p <- ggplot(
      data,
      aes(x = category, y = score, tooltip = tooltip, data_id = category)
    ) +
      geom_bar_interactive(
        stat = "identity",
        fill = "#18bc9c" # Success color of Flatly theme
      ) +
      labs(
        x = "Category",
        y = "Score"
      ) +
      # flip to make horizontal bar chart
      coord_flip() +
      theme_minimal(base_family = "Lato", base_size = 14) +
      theme(legend.position = "none")

    girafe(
      ggobj = p,
      options = list(
        opts_selection(type = "none"),
        opts_sizing(rescale = TRUE),
        opts_tooltip(
          css = "background-color: #f0f0f0; color: #333; padding: 5px; border-radius: 5px;"
        ),
        opts_hover(
          css = "."
        ),
        opts_hover_inv(
          css = "opacity: 0.5;"
        )
      )
    )
  })

  output$suggested_improvements <- renderTable({
    req(analysis_result())

    evals <- analysis_result()$evals

    evals |>
      arrange(score) |>
      mutate(
        Gain = score_after_improvements - score
      ) |>
      select(
        Category = category,
        `Current score` = score,
        Improvements = improvements,
        `Score After Improvements` = score_after_improvements,
        Gain
      ) |>
      arrange(desc(Gain))
  })

  # update value boxes based on analysis_result()$meta
  output$showtime <- renderText({
    req(analysis_result())
    paste0(
      analysis_result()$meta$estimated_duration_minutes,
      " minutes"
    )
  })

  output$code_savviness <- renderText({
    req(analysis_result())
    paste0(analysis_result()$meta$percent_with_code, " %")
  })

  output$image_presence <- renderText({
    req(analysis_result())
    paste0(analysis_result()$meta$percent_with_images, " %")
  })
}

shinyApp(ui, server)
