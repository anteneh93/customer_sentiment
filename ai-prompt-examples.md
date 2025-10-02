# AI Prompt Examples for Vertex AI Gemini

This document contains examples of the AI prompt used for sentiment analysis and topic extraction in the feedback pipeline.

## Prompt Template

```
Analyze the following customer feedback and return a JSON response with sentiment and topics.

Sentiment options: POSITIVE, NEGATIVE, NEUTRAL
Topic options: BILLING, UI_UX, PERFORMANCE, FEATURE_REQUEST

Input: {feedback_text}

Output JSON format:
{
    "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
    "topics": ["<topic1>", "<topic2>", "<topic3>"]
}

Return only the JSON response, no additional text.
```

## Example Inputs and Expected Outputs

### Example 1: Negative Performance Feedback
**Input:**
```
The new dashboard is visually appealing, but it's incredibly slow to load the main widgets. Also, I think there's an issue with how my latest invoice is calculated in the billing section.
```

**Expected Output:**
```json
{
    "sentiment": "NEGATIVE",
    "topics": ["PERFORMANCE", "BILLING"]
}
```

### Example 2: Positive UI/UX Feedback
**Input:**
```
I love the new interface! The design is clean and intuitive. The navigation is much better than before. Great job on the user experience improvements!
```

**Expected Output:**
```json
{
    "sentiment": "POSITIVE",
    "topics": ["UI_UX"]
}
```

### Example 3: Neutral Feature Request
**Input:**
```
It would be nice to have a dark mode option. The current interface is fine, but a dark theme would be appreciated by many users.
```

**Expected Output:**
```json
{
    "sentiment": "NEUTRAL",
    "topics": ["FEATURE_REQUEST", "UI_UX"]
}
```

### Example 4: Negative Billing Feedback
**Input:**
```
I'm very disappointed with the recent billing changes. The new pricing structure is confusing and I was charged more than expected. This is unacceptable.
```

**Expected Output:**
```json
{
    "sentiment": "NEGATIVE",
    "topics": ["BILLING"]
}
```

### Example 5: Mixed Sentiment with Multiple Topics
**Input:**
```
The app works well most of the time, but it crashes frequently on mobile devices. The customer support team was helpful when I contacted them about the billing issue. I'd like to see better error handling and more detailed crash reports.
```

**Expected Output:**
```json
{
    "sentiment": "NEGATIVE",
    "topics": ["PERFORMANCE", "BILLING", "FEATURE_REQUEST"]
}
```

### Example 6: Neutral Technical Feedback
**Input:**
```
The system is working as expected. No major issues to report. The performance seems adequate for our current needs.
```

**Expected Output:**
```json
{
    "sentiment": "NEUTRAL",
    "topics": ["PERFORMANCE"]
}
```

## Topic Definitions

- **BILLING**: Issues related to pricing, invoicing, payment processing, subscription management
- **UI_UX**: User interface design, user experience, navigation, visual design, usability
- **PERFORMANCE**: Speed, responsiveness, system performance, loading times, crashes
- **FEATURE_REQUEST**: Requests for new functionality, enhancements, additional features

## Sentiment Guidelines

- **POSITIVE**: Expresses satisfaction, praise, or positive emotions
- **NEGATIVE**: Expresses dissatisfaction, complaints, or negative emotions
- **NEUTRAL**: Factual statements, suggestions, or balanced feedback without strong emotional tone

## Error Handling

The system handles various error cases:

1. **Invalid JSON Response**: Defaults to `{"sentiment": "NEUTRAL", "topics": []}`
2. **Invalid Sentiment**: Defaults to `"NEUTRAL"`
3. **Invalid Topics**: Filters out invalid topics, keeps only valid ones
4. **Too Many Topics**: Limits to maximum of 3 topics
5. **AI Service Errors**: Defaults to neutral sentiment and empty topics

## Performance Considerations

- The prompt is optimized for fast processing
- JSON response format ensures easy parsing
- Clear instructions reduce ambiguity
- Error handling prevents pipeline failures
