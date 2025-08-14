I will provide you with a slide deck in Markdown. For context, this is a {{ length }}-minute {{ type }} at {{ event }}. 
The audience is {{ audience }}.

To start, please extract the following meta-data: 
- The number of slides
- The percentage of slides containing code blocks
- The percentage of slides containing images 

Return only the JSON results, nothing else.

I have an HTML file that can be used to improve your analysis, the path to the HTML file is:
{{ html_file_path }}

Here are the slides in Markdown:
{{ markdown }}
