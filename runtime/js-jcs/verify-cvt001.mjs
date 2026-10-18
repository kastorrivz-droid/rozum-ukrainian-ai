import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { canonicalizeUtf8 } from "./canonicalize.mjs";


const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const CVT001 = resolve(ROOT, "tests/interoperability/CVT-001");
const CVT002 = resolve(ROOT, "tests/interoperability/CVT-002");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function buildSigningInput(envelope) {
  const fields = [
    "ROZUM_v2_SIG",
    envelope.protocol_version,
    envelope.id,
    envelope.timestamp,
    envelope.sender_id,
    envelope.key_id,
    envelope.author.id,
    envelope.author.role,
    envelope.intent,
    sha256(canonicalizeUtf8(envelope.context)),
    sha256(canonicalizeUtf8(envelope.data)),
    sha256(Buffer.from(envelope.question, "utf8")),
    envelope.output_format,
  ];
  return Buffer.from(fields.join(":"), "utf8");
}

const assertions = [];
function check(name, condition) {
  assertions.push({ name, status: condition ? "PASS" : "FAIL" });
}

const envelope = readJson(resolve(CVT001, "envelope.unsigned.json"));
const actualSigningInput = buildSigningInput(envelope);
const expectedSigningInput = readFileSync(resolve(CVT001, "signing_input.bin"));
const expectedDigest = readFileSync(resolve(CVT001, "signing_input.sha256"), "ascii").trim();

check("CVT-001 exact signing bytes", actualSigningInput.equals(expectedSigningInput));
check("CVT-001 signing SHA-256", sha256(actualSigningInput) === expectedDigest);

const vectors = readJson(resolve(CVT002, "jcs_vectors.json"));
for (const vector of vectors.vectors) {
  const actualHex = canonicalizeUtf8(vector.value).toString("hex");
  check(`JCS vector: ${vector.name}`, actualHex === vector.expected_utf8_hex);
}

let rejectedLoneSurrogate = false;
try {
  canonicalizeUtf8("\ud800");
} catch (error) {
  rejectedLoneSurrogate = error instanceof TypeError;
}
check("JCS rejects lone surrogate", rejectedLoneSurrogate);

let rejectedNonFinite = false;
try {
  canonicalizeUtf8(Number.POSITIVE_INFINITY);
} catch (error) {
  rejectedNonFinite = error instanceof TypeError;
}
check("JCS rejects non-finite number", rejectedNonFinite);

const result = {
  suite: "PRE-CVT-002 independent JCS",
  implementation: "Node.js standard library",
  runtime: process.version,
  status: assertions.every((item) => item.status === "PASS") ? "PASS" : "FAIL",
  assertions,
};

if (process.argv.includes("--json")) {
  process.stdout.write(`${JSON.stringify(result)}\n`);
} else {
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (result.status !== "PASS") process.exitCode = 1;
