I will provide you with a slide deck in Markdown. For context, this is a {{ length }}-minute {{ type }} at {{ event }}. 
The audience is {{ audience }}.

You need to extract meta-data and you need to analyse the content and provide suggestions for improvements. 
Please extract data according to the provided data model. 
Return the result as a JSON object that conforms to that provided data model.

Keep improvements concise and mention the slide number where possible. 
Only suggest improvements if they are clearly warranted. 
Do not invent issues if the content is already solid.

Here are the slides in Markdown:
{{ markdown }}
