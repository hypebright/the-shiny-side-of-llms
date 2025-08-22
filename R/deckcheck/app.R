library(shiny)
library(bslib)
library(ellmer)
library(ggplot2)
library(ggiraph)
library(gdtools)

# Register Monteserrat font
register_gfont("Lato")

ui <- page_fillable(
  ## General theme and styles
  theme = bs_theme(bootswatch = "flatly"),
  tags$style(HTML(
    "
    #suggested_improvements table {
      font-family: 'Lato', sans-serif;
      font-size: 16px;
    }
  "
  )),
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
      actionButton(
        inputId = "submit",
        label = shiny::tagList(
          bsicons::bs_icon("robot"),
          "Analyse presentation"
        )
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
        value = "9 minutes",
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
        value = "15%",
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
        value = "7%",
        showcase = bsicons::bs_icon("file-image"),
        theme = "primary"
      )
    ),
    layout_column_wrap(
      fill = FALSE,
      width = 1 / 2,
      ### Graph with scoring metrics
      card(
        card_header(
          strong("Scores per category, before and after suggested improvements")
        ),
        girafeOutput(
          outputId = "scores"
        )
      ),
      ### Table with suggested improvements
      card(
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
  output$scores <- renderGirafe({
    # Placeholder for the plot output, simple bar chart with ggplot2
    data <- data.frame(
      Category = c("Metric 1", "Metric 2", "Metric 3"),
      Score = c(4, 8, 9),
      Tooltip = c(
        "Score for Metric 1",
        "Score for Metric 2",
        "Score for Metric 3"
      )
    )
    # set fill to
    p <- ggplot(
      data,
      aes(x = Category, y = Score, tooltip = Tooltip, data_id = Category)
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
    # Placeholder for the table output
    data.frame(
      Improvement = c("Add more images", "Reduce code complexity"),
      Impact = c("High", "Medium")
    )
  })
}

shinyApp(ui, server)
