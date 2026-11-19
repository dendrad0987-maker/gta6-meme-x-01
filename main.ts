// gta6-meme-x-01 entrypoint.
//
// The whole job of this program is small: take the POST.json that names the
// X post carrying the GTA 6 meme, and hand it to the grader by placing a copy
// in the output folder. The meme itself lives in the post on X (its first
// picture plus its text); nothing written here is judged, this file only
// ferries the link to where the gate looks for it.
//
// Where the two folders live can be overridden for a local run:
//   mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts
// Inside the grader they default to /bot and /output.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

function fail(message: string): never {
  console.error(`main.ts: ${message}`);
  process.exit(1);
}

// Resolve the two directories, falling back to the grader's paths.
const botFolder = process.env.MAKEFUN_BOT_DIR ?? '/bot';
const outFolder = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';

const sourcePath = resolve(join(botFolder, 'POST.json'));
const targetPath = resolve(join(outFolder, 'POST.json'));

// Bail out early with a clear message when there is nothing to copy.
if (!existsSync(sourcePath)) {
  fail(`no POST.json found in ${botFolder}`);
}

let rawText: string;
try {
  rawText = readFileSync(sourcePath, 'utf8');
} catch (problem) {
  fail(`could not read ${sourcePath}: ${(problem as Error).message}`);
}

// The gate only accepts a real post address, so check the payload carries
// one before copying anything: a JSON object whose url is an https link.
let parsed: unknown;
try {
  parsed = JSON.parse(rawText!);
} catch {
  fail(`POST.json in ${botFolder} is not valid JSON`);
}

const link =
  parsed !== null && typeof parsed === 'object'
    ? (parsed as Record<string, unknown>).url
    : undefined;

if (typeof link !== 'string' || !link.startsWith('https://')) {
  fail(`POST.json in ${botFolder} has no valid https URL`);
}

// Make sure the destination folder exists, then pass the file through
// exactly as it stands so the copy is byte-identical to the original.
mkdirSync(outFolder, { recursive: true });
try {
  writeFileSync(targetPath, rawText!, 'utf8');
} catch (problem) {
  fail(`could not write ${targetPath}: ${(problem as Error).message}`);
}
