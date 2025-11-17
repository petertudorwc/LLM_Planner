import React from 'react';
import { Box, Typography } from '@mui/material';

function FormattedMessage({ content }) {
  // Parse the content and format it appropriately
  const formatContent = (text) => {
    const lines = text.split('\n');
    const elements = [];
    let currentList = [];
    let inList = false;

    lines.forEach((line, index) => {
      // Check for numbered list items (1. 2. 3. etc.)
      const numberedMatch = line.match(/^(\d+)\.\s+\*\*(.*?)\*\*/);
      if (numberedMatch) {
        if (!inList) {
          inList = true;
          currentList = [];
        }
        // Extract the title and remaining content
        const [, number, title] = numberedMatch;
        const rest = line.substring(numberedMatch[0].length).trim();
        currentList.push(
          <Box key={`item-${index}`} sx={{ mb: 2, pl: 2 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 0.5 }}>
              {number}. {title}
            </Typography>
            {rest && (
              <Typography variant="body2" sx={{ pl: 2, whiteSpace: 'pre-line' }}>
                {parseInlineFormatting(rest)}
              </Typography>
            )}
          </Box>
        );
        return;
      }

      // Check for bullet points starting with dashes or bullet-like markers
      const bulletMatch = line.match(/^\s*[-•]\s+\*\*(.*?)\*\*:\s*(.*)/);
      if (bulletMatch) {
        if (!inList) {
          inList = true;
          currentList = [];
        }
        const [, label, value] = bulletMatch;
        currentList.push(
          <Box key={`bullet-${index}`} sx={{ display: 'flex', mb: 0.5, pl: 3 }}>
            <Typography variant="body2" sx={{ fontWeight: 'bold', minWidth: '120px' }}>
              {label}:
            </Typography>
            <Typography variant="body2">{parseInlineFormatting(value)}</Typography>
          </Box>
        );
        return;
      }

      // Check for plain bullet points
      const simpleBulletMatch = line.match(/^\s*[-•]\s+(.*)/);
      if (simpleBulletMatch) {
        if (!inList) {
          inList = true;
          currentList = [];
        }
        currentList.push(
          <Typography key={`simple-bullet-${index}`} variant="body2" sx={{ pl: 3, mb: 0.5 }}>
            • {parseInlineFormatting(simpleBulletMatch[1])}
          </Typography>
        );
        return;
      }

      // If we were in a list and now we're not, flush the list
      if (inList && line.trim() !== '') {
        elements.push(
          <Box key={`list-${elements.length}`} sx={{ mb: 2 }}>
            {currentList}
          </Box>
        );
        currentList = [];
        inList = false;
      }

      // Handle regular lines
      if (line.trim()) {
        // Check for standalone bold text (questions or headers)
        if (line.includes('**')) {
          elements.push(
            <Typography key={`text-${index}`} variant="body1" sx={{ mb: 1 }}>
              {parseInlineFormatting(line)}
            </Typography>
          );
        } else {
          elements.push(
            <Typography key={`text-${index}`} variant="body1" sx={{ mb: 1 }}>
              {line}
            </Typography>
          );
        }
      } else if (!inList) {
        // Empty line (but not within a list)
        elements.push(<Box key={`space-${index}`} sx={{ height: '8px' }} />);
      }
    });

    // Flush any remaining list items
    if (currentList.length > 0) {
      elements.push(
        <Box key={`list-final`} sx={{ mb: 2 }}>
          {currentList}
        </Box>
      );
    }

    return elements;
  };

  // Helper function to parse inline formatting like **bold**
  const parseInlineFormatting = (text) => {
    const parts = [];
    let lastIndex = 0;
    const boldRegex = /\*\*(.*?)\*\*/g;
    let match;

    while ((match = boldRegex.exec(text)) !== null) {
      // Add text before the match
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      // Add the bold text
      parts.push(
        <strong key={`bold-${match.index}`} style={{ fontWeight: 600 }}>
          {match[1]}
        </strong>
      );
      lastIndex = match.index + match[0].length;
    }

    // Add any remaining text
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  return (
    <Box sx={{ '& > *:last-child': { mb: 0 } }}>
      {formatContent(content)}
    </Box>
  );
}

export default FormattedMessage;
