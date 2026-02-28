import * as fs from 'fs';
import * as path from 'path';

/**
 * Écrire les résultats du test dans le fichier output
 */
export async function writeTestOutput(
  testResult: any,
  forumId: string
): Promise<void> {
  const outputDir = path.join(process.cwd(), 'Ai');
  const outputFile = path.join(outputDir, 'testOutput.md');

  // Créer le répertoire s'il n'existe pas
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Formater le résultat
  const timestamp = new Date().toISOString();
  const content = formatTestResult(testResult, forumId, timestamp);

  // Lire le fichier existant ou créer un nouveau
  let existingContent = '';
  if (fs.existsSync(outputFile)) {
    existingContent = fs.readFileSync(outputFile, 'utf-8');
  }

  // Ajouter le nouveau résultat
  const updatedContent = existingContent + '\n' + content;

  // Écrire le fichier
  fs.writeFileSync(outputFile, updatedContent, 'utf-8');

  console.log(`📝 Test output written to: ${outputFile}`);
}

/**
 * Formater le résultat du test en Markdown
 */
function formatTestResult(
  result: any,
  forumId: string,
  timestamp: string
): string {
  let markdown = `
---

## Test: ${result.testName}

**Timestamp**: ${timestamp}  
**Forum ID**: ${forumId}  
**Status**: ${result.status}  
**Duration**: ${(result.duration / 1000).toFixed(2)}s  

### Configuration
\`\`\`json
${JSON.stringify(result.config || {}, null, 2)}
\`\`\`

### Results
- **Total Logs**: ${result.totalLogs}
- **Total Logs by State**: ${JSON.stringify(result.logsCounts || result.logsCount || {})}

`;

  // Ajouter les metrics si présentes
  if (result.metrics) {
    markdown += `
### Metrics
- **Success Rate**: ${result.metrics.successRate.toFixed(2)}%
- **Throughput**: ${result.metrics.throughput.toFixed(2)} posts/sec
- **Total Duration**: ${(result.metrics.totalDuration / 1000).toFixed(2)}s
- **Errors**: ${result.metrics.totalErrors}
- **Retries**: ${result.metrics.retries}

#### States Timeline
\`\`\`
`;
    result.metrics.states.forEach((state: any) => {
      markdown += `
${state.state}:
  Count: ${state.count}
  Avg Duration: ${state.avgDuration.toFixed(2)}ms
`;
    });
    markdown += '```\n';
  }

  // Ajouter les détails des erreurs s'il y en a
  if (result.errors && result.errors.length > 0) {
    markdown += `\n### ⚠️ Errors Detail\n`;
    result.errors.forEach((err: any, index: number) => {
      markdown += `\n**Error ${index + 1}:**\n`;
      markdown += `\`\`\`json\n${JSON.stringify(err, null, 2)}\n\`\`\`\n`;
    });
  }

  // Ajouter une ligne de séparation finale
  markdown += `\n---\n`;

  return markdown;
}