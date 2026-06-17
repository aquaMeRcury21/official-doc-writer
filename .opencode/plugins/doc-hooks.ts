import type { Plugin } from "@opencode-ai/plugin";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";

export const DocHooksPlugin: Plugin = async ({ client, $, directory }) => {
  const sessionDocxs: string[] = [];

  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool !== "bash") return;

      const cmd: string = input?.args?.command || "";
      const stdout: string = output?.result || "";

      // detect docx path from bash output or command string
      const docxPath = pickDocxPath(stdout) || pickDocxPath(cmd);
      if (!docxPath || !existsSync(docxPath)) return;

      sessionDocxs.push(docxPath);

      // validate format
      const validateScript = resolve(
        directory,
        ".opencode/skills/doc-format/scripts/validate_docx.py"
      );
      if (existsSync(validateScript)) {
        await $`python ${validateScript} "${docxPath}"`;
      }

      client.app.log({
        body: {
          service: "doc-hooks",
          level: "info",
          message: `公文已生成: ${docxPath}`,
        },
      });
    },

    event: async ({ event }) => {
      if (event.type === "session.idle" && sessionDocxs.length > 0) {
        client.app.log({
          body: {
            service: "doc-hooks",
            level: "info",
            message:
              `本会话共生成 ${sessionDocxs.length} 份公文。` +
              `可执行 /校对 审核，或 /归档 归档。`,
          },
        });
        sessionDocxs.length = 0;
      }
    },
  };
};

function pickDocxPath(text: string): string | null {
  const matches = text.match(/[^\s"']+\.docx["']?/g);
  if (!matches) return null;
  for (const m of matches) {
    const clean = m.replace(/["']/g, "");
    if (existsSync(clean)) return resolve(clean);
  }
  return null;
}
