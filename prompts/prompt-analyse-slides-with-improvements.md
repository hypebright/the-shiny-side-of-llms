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

Additionally, suggest any improvements to:

1. Pacing and structure: flag slides where pacing might be too fast or too slow based on the content density. Suggest if slides can be combined or split.
2. Visual clarity or design: flag slides that are too text-heavy or cluttered and recommend slide redesign like splitting text, adding visuals or adding bullet points.
3. Storytelling or logical flow: check if the presentation can be improved by adding a motivating opening, summarizing key points before transitions and a clear closure.
4. Consistency of style and structure: flag sudden shifts in slide formatting, tone, and visual elements that feel unintentional.
5. Engagement with the audience: check if the presentation can be improved by adding interactive elements like questions, polls and demos, while keeping the time constraint in mind.
6. Accessibility: flag slides with small text, poor color contrast, or a visual overload.

Keep improvements concise and mention the slide number where possible. 
Only suggest improvements if they are clearly warranted. 
Do not invent issues if the content is already solid.

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
  },
  "suggested_improvements": {
    "pacing": "",
    "visual_design": "",
    "storytelling": "",
    "consistency": "",
    "engagement": "",
    "accessibility": ""
  }
}

For any improvement category that doesn't require feedback, set its value to null.

Here are the slides in Markdown:
{{ markdown }}
