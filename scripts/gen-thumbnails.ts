#!/usr/bin/env ts-node
/**
 * Batch converts raw opponent headshots into lightweight 32px WebP thumbnails.
 *
 * Usage: `pnpm ts-node scripts/gen-thumbnails.ts --input ./data/headshots --output ./frontend/public/img/opponents`
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

interface CliOptions {
  inputDir: string;
  outputDir: string;
  size: number;
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEFAULTS: CliOptions = {
  inputDir: path.resolve(__dirname, '../data/raw_headshots'),
  outputDir: path.resolve(__dirname, '../frontend/public/img/opponents'),
  size: 32,
};

const parseArgs = (): CliOptions => {
  const args = process.argv.slice(2);
  const options: Partial<CliOptions> = {};
  for (let index = 0; index < args.length; index += 2) {
    const key = args[index];
    const value = args[index + 1];
    if (!value) continue; // eslint-disable-line no-continue
    if (key === '--input') {
      options.inputDir = path.resolve(process.cwd(), value);
    } else if (key === '--output') {
      options.outputDir = path.resolve(process.cwd(), value);
    } else if (key === '--size') {
      options.size = Number.parseInt(value, 10);
    }
  }
  return {
    inputDir: options.inputDir ?? DEFAULTS.inputDir,
    outputDir: options.outputDir ?? DEFAULTS.outputDir,
    size: options.size ?? DEFAULTS.size,
  };
};

const ensureDirectory = async (dir: string) => {
  await fs.mkdir(dir, { recursive: true });
};

const supportedExtensions = new Set(['.jpg', '.jpeg', '.png', '.webp']);

const buildDestinationPath = (outputDir: string, filename: string, size: number): string => {
  const base = path.parse(filename).name;
  return path.join(outputDir, `${base}-${size}.webp`);
};

const processImage = async (inputPath: string, outputPath: string, size: number) => {
  await sharp(inputPath)
    .resize(size, size, { fit: 'cover', position: 'centre' })
    .webp({ quality: 80, effort: 4 })
    .toFile(outputPath);
};

const main = async () => {
  const { inputDir, outputDir, size } = parseArgs();
  await ensureDirectory(outputDir);
  const entries = await fs.readdir(inputDir, { withFileTypes: true });
  const tasks: Promise<void>[] = [];

  for (const entry of entries) {
    if (!entry.isFile()) {
      continue;
    }
    const extension = path.extname(entry.name).toLowerCase();
    if (!supportedExtensions.has(extension)) {
      continue;
    }

    const sourcePath = path.join(inputDir, entry.name);
    const destinationPath = buildDestinationPath(outputDir, entry.name, size);
    tasks.push(
      processImage(sourcePath, destinationPath, size).catch((error) => {
        console.error(`Failed to process ${entry.name}:`, error);
      }),
    );
  }

  await Promise.all(tasks);
  console.log(`Processed ${tasks.length} thumbnails into ${outputDir}`);
};

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
