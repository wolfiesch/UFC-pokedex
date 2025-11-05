/**
 * @fileoverview Utility script that leverages Sharp to convert high-resolution opponent
 * photos into the 32px WebP thumbnails consumed by the FightScatter visualization.
 *
 * Usage (from repository root):
 *   pnpm dlx ts-node scripts/gen-thumbnails.ts --source ./raw --dest ./public/img/opponents
 */

import fs from 'node:fs';
import path from 'node:path';
import { promisify } from 'node:util';

type SharpModule = typeof import('sharp');

const readdir = promisify(fs.readdir);
const stat = promisify(fs.stat);

interface CliOptions {
  /** Absolute or relative path pointing to the directory containing original images. */
  source: string;
  /** Destination directory that will receive the optimized thumbnails. */
  dest: string;
  /** Optional override for the output dimension (defaults to 32px square). */
  size?: number;
}

/**
 * Parses CLI arguments of the form `--key value` into a structured object.
 */
const parseArgs = (): CliOptions => {
  const args = process.argv.slice(2);
  const options: Record<string, string> = {};
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i];
    const value = args[i + 1];
    if (!key?.startsWith('--') || !value) {
      continue;
    }
    options[key.slice(2)] = value;
  }
  if (!options.source || !options.dest) {
    throw new Error('Both --source and --dest arguments are required.');
  }
  return {
    source: options.source,
    dest: options.dest,
    size: options.size ? Number(options.size) : 32,
  };
};

/**
 * Ensures the destination directory exists prior to writing thumbnails.
 */
const ensureDirectory = async (dir: string): Promise<void> => {
  await fs.promises.mkdir(dir, { recursive: true });
};

/**
 * Processes a single source image and writes the resized WebP thumbnail.
 */
const loadSharp = async (): Promise<SharpModule> => {
  try {
    return await import('sharp');
  } catch (error) {
    throw new Error(
      'The `sharp` package must be installed (e.g., `pnpm add -D sharp`) before running this script.',
    );
  }
};

const processImage = async (sourcePath: string, destPath: string, size: number): Promise<void> => {
  const sharp = await loadSharp();
  await sharp(sourcePath)
    .resize(size, size, { fit: 'cover' })
    .webp({ quality: 85 })
    .toFile(destPath);
};

/**
 * Recursively walks the source directory collecting image file paths.
 */
const collectImages = async (dir: string): Promise<string[]> => {
  const entries = await readdir(dir);
  const results: string[] = [];
  await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(dir, entry);
      const info = await stat(fullPath);
      if (info.isDirectory()) {
        const subEntries = await collectImages(fullPath);
        results.push(...subEntries);
        return;
      }
      if (/\.(png|jpg|jpeg|webp)$/i.test(entry)) {
        results.push(fullPath);
      }
    }),
  );
  return results;
};

const main = async (): Promise<void> => {
  const { source, dest, size = 32 } = parseArgs();
  await ensureDirectory(dest);
  const images = await collectImages(source);
  await Promise.all(
    images.map(async (imagePath) => {
      const fileName = `${path.parse(imagePath).name}-32.webp`;
      const destPath = path.join(dest, fileName);
      await processImage(imagePath, destPath, size);
      // eslint-disable-next-line no-console -- CLI utility feedback is intentional.
      console.log(`Generated ${destPath}`);
    }),
  );
};

main().catch((error) => {
  // eslint-disable-next-line no-console -- CLI utility feedback is intentional.
  console.error('Thumbnail generation failed:', error);
  process.exitCode = 1;
});
