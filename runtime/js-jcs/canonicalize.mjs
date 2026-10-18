const HIGH_SURROGATE_MIN = 0xd800;
const HIGH_SURROGATE_MAX = 0xdbff;
const LOW_SURROGATE_MIN = 0xdc00;
const LOW_SURROGATE_MAX = 0xdfff;

function assertValidUnicode(value) {
  for (let index = 0; index < value.length; index += 1) {
    const unit = value.charCodeAt(index);
    if (unit >= HIGH_SURROGATE_MIN && unit <= HIGH_SURROGATE_MAX) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= LOW_SURROGATE_MIN && next <= LOW_SURROGATE_MAX)) {
        throw new TypeError("JCS rejects lone UTF-16 surrogates");
      }
      index += 1;
    } else if (unit >= LOW_SURROGATE_MIN && unit <= LOW_SURROGATE_MAX) {
      throw new TypeError("JCS rejects lone UTF-16 surrogates");
    }
  }
}

export function canonicalize(value) {
  if (value === null) return "null";

  if (typeof value === "boolean") return value ? "true" : "false";

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new TypeError("JCS rejects non-finite numbers");
    }
    return JSON.stringify(value);
  }

  if (typeof value === "string") {
    assertValidUnicode(value);
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    const items = [];
    for (let index = 0; index < value.length; index += 1) {
      if (!Object.hasOwn(value, index)) {
        throw new TypeError("JCS does not support sparse arrays");
      }
      items.push(canonicalize(value[index]));
    }
    return `[${items.join(",")}]`;
  }

  if (typeof value === "object") {
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
      throw new TypeError("JCS accepts only JSON objects");
    }
    const entries = Object.keys(value)
      .sort()
      .map((key) => {
        assertValidUnicode(key);
        return `${JSON.stringify(key)}:${canonicalize(value[key])}`;
      });
    return `{${entries.join(",")}}`;
  }

  throw new TypeError(`JCS does not support values of type ${typeof value}`);
}

export function canonicalizeUtf8(value) {
  return Buffer.from(canonicalize(value), "utf8");
}
