import * as fs from "fs/promises";
import * as path from "path";
import { fileURLToPath } from "url";
import type { QueueInspection } from "./queue.js";

// Pour obtenir __dirname en ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REPORT_PATH = path.join(__dirname, "../../Ai/testOutput.md");

/**
 * Interface pour les données de rapport
 */
export interface TestReportData {
  testName: string;
  queueInspection?: QueueInspection;
  customData?: Record<string, unknown>;
  status: "PASS" | "FAIL" | "PENDING";
  duration?: number;
}

/**
 * Génère un rapport en Markdown et l'ajoute au fichier testOutput.md
 * Crée le fichier s'il n'existe pas
 */
export async function writeTestReport(reportData: TestReportData): Promise<void> {
  const timestamp = new Date().toISOString();
  
  let content = formatReportMarkdown(reportData, timestamp);

  try {
    // Vérifie si le fichier existe
    await fs.access(REPORT_PATH);
    // File exists, append
    const existingContent = await fs.readFile(REPORT_PATH, "utf-8");
    content = existingContent + "\n" + content;
  } catch {
    // File doesn't exist, will be created
  }

  await fs.writeFile(REPORT_PATH, content, "utf-8");
}

/**
 * Formate les données du rapport en Markdown
 */
function formatReportMarkdown(reportData: TestReportData, timestamp: string): string {
  let markdown = `## Test: ${reportData.testName}\n`;
  markdown += `**Timestamp:** ${timestamp}\n`;
  markdown += `**Status:** ${reportData.status}\n`;
  
  if (reportData.duration) {
    markdown += `**Duration:** ${reportData.duration}ms\n`;
  }

  markdown += "\n---\n\n";

  // Ajoute les données de la queue si présentes
  if (reportData.queueInspection) {
    markdown += `### Queue Inspection Results\n\n`;
    markdown += `**Total Jobs:** ${reportData.queueInspection.totalCount}\n\n`;
    
    if (reportData.queueInspection.jobs.length > 0) {
      markdown += `#### Jobs Details\n\n`;
      markdown += `| ID | Name | Status | Progress | Data |\n`;
      markdown += `|----|------|--------|----------|------|\n`;
      
      reportData.queueInspection.jobs.forEach((job) => {
        const dataStr = JSON.stringify(job.data).substring(0, 50);
        const status = job.status || "unknown";
        const progress = job.progress !== null ? `${job.progress}%` : "N/A";
        markdown += `| ${job.id} | ${job.name} | ${status} | ${progress} | ${dataStr}... |\n`;
      });
      
      markdown += "\n";
      
      // Ajoute les détails complets en JSON collapsible
      markdown += `<details>\n`;
      markdown += `<summary>Full Queue Data (JSON)</summary>\n\n`;
      markdown += `\`\`\`json\n`;
      markdown += JSON.stringify(reportData.queueInspection, null, 2);
      markdown += `\n\`\`\`\n`;
      markdown += `</details>\n\n`;
    }
  }

  // Ajoute les données personnalisées si présentes
  if (reportData.customData && Object.keys(reportData.customData).length > 0) {
    markdown += `### Custom Data\n\n`;
    markdown += `\`\`\`json\n`;
    markdown += JSON.stringify(reportData.customData, null, 2);
    markdown += `\n\`\`\`\n\n`;
  }

  markdown += `---\n\n`;

  return markdown;
}

/**
 * Fonction utilitaire pour nettoyer tous les rapports (optionnel)
 */
export async function clearTestReports(): Promise<void> {
  try {
    await fs.unlink(REPORT_PATH);
  } catch {
    // File doesn't exist, nothing to delete
  }
}
