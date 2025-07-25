I will provide you with a slide deck in Markdown. For context, this is a {{ length }}-minute {{ type }} at {{ event }}. 
The audience is {{ audience }}.

Please extract the following information:

1. The presentation title
2. Total number of slides
3. Percentage of slides containing code blocks
4. Percentage of slides containing images
5. Estimated presentation length (in minutes, assuming ~1 minute per text slide and 2–3 minutes per code or image-heavy slide)
6. Clarity of content (rate from 1–10 and give a concise explanation)
7. Tone (a brief description)
8. Relevance for intended audience (rate from 1–10 and give a concise explanation)

Return your answer as a JSON object with the following structure:

{
  "presentation_title": "",
  "total_slides": 0,
  "percent_with_code": 0,
  "percent_with_images": 0,
  "estimated_duration_minutes": 0,
  "clarity_score": {
    "score": 0,
    "justification": ""
  },
  "tone": "",
  "relevance_for_audience": {
    "score": 0,
    "justification": ""
  }
}

Here are the slides in Markdown:
{{markdown}}
