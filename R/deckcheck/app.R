library(shiny)
library(ellmer)

ui <- fluidPage(
  titlePanel("Analyze a Quarto Presentation (.qmd)"),
  sidebarLayout(
    sidebarPanel(
      fileInput("qmd_file", "Upload a .qmd file", accept = ".qmd"),
      actionButton("analyze", "Analyze")
    ),
    mainPanel(
      verbatimTextOutput("llm_response")
    )
  )
)

server <- function(input, output, session) {
  qmd_text <- eventReactive(input$analyze, {
    req(input$qmd_file)
    readLines(input$qmd_file$datapath, warn = FALSE) |> paste(collapse = "\n")
  })

  llm_result <- reactive({
    req(qmd_text())

    prompt <- paste(
      "Please analyze the following Quarto presentation (.qmd) and provide a summary or suggestions for improvement:\n\n",
      qmd_text()
    )

    ellmer::chat_anthropic(system_prompt = prompt)
  })

  output$llm_response <- renderText({
    req(llm_result())
    llm_result()
  })
}

shinyApp(ui, server)
