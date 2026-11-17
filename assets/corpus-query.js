/* ANNIS-inspired, ordered annotation queries over TEI <w> morphemes.
 * User-supplied regular expressions must be executed in the search worker,
 * where the page can terminate an expensive expression without freezing UI.
 *
 * Errors are QueryError objects: `code` is the class of failure, `detail` names
 * the exact problem (the page translates it), `position` is the 0-based
 * character offset in the query when one is known. `message` is English.
 */
(function(root, factory){
  const api = factory();
  if(typeof module === "object" && module.exports) module.exports = api;
  else root.CorpusQuery = api;
})(typeof self !== "undefined" ? self : globalThis, function(){
  "use strict";

  const LIMITS = Object.freeze({queryLength:4096, nodes:16, distance:1000, results:2000, operations:2000000});
  const ANNOTATIONS = Object.freeze({tok:"form", form:"form", lemma:"lemma", pos:"pos", type:"pos", msd:"msd"});
  const normalizeWord = value => String(value == null ? "" : value).normalize("NFD")
    .replace(/[̀-ͯ︠-︯]/g, "").normalize("NFC").toLowerCase();

  class QueryError extends Error {
    constructor(code, message, position, detail){
      super(message);
      this.name = "QueryError";
      this.code = code;
      if(position != null) this.position = position;
      if(detail != null) this.detail = detail;
    }
  }

  function compile(query, mode){
    if(mode == null) mode = "aql";
    if(mode !== "aql" && mode !== "pos") throw new QueryError("INVALID_MODE", "Choose POS sequence or annotation query mode.", null, "mode");
    query = String(query == null ? "" : query);
    if(query.length > LIMITS.queryLength) throw new QueryError("QUERY_LIMIT", "Queries may contain at most " + LIMITS.queryLength + " characters.", null, "tooLong");
    if(!query.trim()) throw new QueryError("EMPTY_QUERY", "Enter a query.", null, "empty");

    if(mode === "pos"){
      const tags = query.trim().split(/\s+/);
      if(tags.length > LIMITS.nodes) throw new QueryError("QUERY_LIMIT", "A query may contain at most " + LIMITS.nodes + " morphemes.", null, "tooManyNodes");
      if(tags.some(tag => !/^[\p{L}][\p{L}\p{N}_-]*$/u.test(tag))){
        throw new QueryError("SYNTAX_ERROR", "Separate exact POS tags with spaces, for example: ART N V.", null, "posTags");
      }
      return {nodes:tags.map(value => ({annotation:"pos", kind:"literal", value})),
        distances:tags.slice(1).map(() => ({min:1, max:1}))};
    }

    let at = 0;
    const nodes = [], distances = [];
    const skipSpace = () => { while(at < query.length && /\s/.test(query[at])) at++; };
    const syntax = (detail, message, position) => {
      if(position == null) position = at;
      throw new QueryError("SYNTAX_ERROR", message + " (character " + (position + 1) + ").", position, detail);
    };

    function readString(){
      const start = at++;
      while(at < query.length){
        if(query[at] === "\\"){
          at += 2;
        }else if(query[at++] === '"'){
          try{ return JSON.parse(query.slice(start, at)); }
          catch(_){ syntax("badString", "Use a valid double-quoted string", start); }
        }
      }
      syntax("openString", "Close the double-quoted string", start);
    }

    function readRegex(){
      const start = ++at;
      let inClass = false;
      while(at < query.length){
        const ch = query[at];
        if(ch === "\\"){
          at += 2;
          continue;
        }
        if(ch === "[") inClass = true;
        else if(ch === "]") inClass = false;
        else if(ch === "/" && !inClass){
          const source = query.slice(start, at++);
          try{
            // The pattern must be complete on its own: otherwise "a)|(b" would
            // close the group added below and escape the anchors.
            new RegExp(source, "u");
            // The entire annotation must match, as in ANNIS. The group keeps an
            // alternation such as N|V inside the anchors; without the m flag,
            // $ matches only at the very end of the value.
            return {source, regex:new RegExp("^(?:" + source + ")$", "u")};
          }catch(error){
            const reason = String(error && error.message || "").replace(/^.*:\s*/, "");
            const failure = new QueryError("INVALID_REGEX", "Invalid Unicode JavaScript regular expression" + (reason ? ": " + reason : "") + ".", start, "badRegex");
            if(reason) failure.reason = reason;
            throw failure;
          }
        }
        at++;
      }
      syntax("openRegex", "Close the regular expression with /", start - 1);
    }

    function readNode(){
      skipSpace();
      const name = /^[A-Za-z][A-Za-z0-9_]*/.exec(query.slice(at));
      if(!name) syntax("expectedNode", 'Expected an annotation, for example pos="N"');
      if(!Object.prototype.hasOwnProperty.call(ANNOTATIONS, name[0])) syntax("unknownAnnotation", "Supported annotations: tok, form, lemma, pos, type, msd");
      at += name[0].length;
      const annotation = ANNOTATIONS[name[0]];
      skipSpace();
      if(query[at] !== "="){
        if(name[0] === "tok") return {annotation:"form", kind:"any"};
        syntax("expectedEquals", 'Expected = followed by "value" or /pattern/');
      }
      at++;
      skipSpace();
      if(query[at] === '"'){
        let value = readString();
        if(annotation === "form" || annotation === "lemma") value = normalizeWord(value);
        return {annotation, kind:"literal", value};
      }
      if(query[at] === "/") return Object.assign({annotation, kind:"regex"}, readRegex());
      syntax("expectedValue", 'Expected a double-quoted value or /regular expression/');
    }

    nodes.push(readNode());
    skipSpace();
    while(at < query.length){
      if(query[at] !== ".") syntax("expectedOperator", "Connect morphemes with . or .min,max; other AQL operators are not supported");
      const operator = at++;
      skipSpace();
      if(query[at] === "*") syntax("unboundedDistance", "Unbounded distance (.*) is not supported; give a range such as .1," + LIMITS.distance, operator);
      let min = 1, max = 1;
      const first = /^\d+/.exec(query.slice(at));
      if(first){
        min = max = Number(first[0]);
        at += first[0].length;
        if(query[at] === ","){
          at++;
          const last = /^\d+/.exec(query.slice(at));
          if(!last) syntax("expectedMax", "Specify the maximum distance after the comma");
          max = Number(last[0]);
          at += last[0].length;
        }
        if(!Number.isSafeInteger(min) || !Number.isSafeInteger(max) || max > LIMITS.distance){
          throw new QueryError("QUERY_LIMIT", "Distances may be at most " + LIMITS.distance + " morphemes.", operator, "tooFar");
        }
        if(min < 1 || max < min) syntax("badDistance", "Distances must satisfy 1 <= minimum <= maximum", operator);
      }
      if(nodes.length >= LIMITS.nodes) throw new QueryError("QUERY_LIMIT", "A query may contain at most " + LIMITS.nodes + " morphemes.", operator, "tooManyNodes");
      distances.push({min, max});
      nodes.push(readNode());
      skipSpace();
    }
    return {nodes, distances};
  }

  function testNode(node, token){
    if(node.kind === "any") return true;
    const raw = String(token[node.annotation] == null ? "" : token[node.annotation]);
    if(node.kind === "regex") return node.regex.test(raw.normalize("NFC"));
    const value = node.annotation === "form" || node.annotation === "lemma" ? normalizeWord(raw) : raw;
    return value === node.value;
  }

  function search(compiled, segments, options){
    options = options || {};
    const selected = Array.isArray(options.selectedWitnesses) ? new Set(options.selectedWitnesses) : null;
    const excluded = new Set(options.excludedPos || []);
    const limit = Number.isFinite(options.limit) ? Math.max(1, Math.min(LIMITS.results, Math.floor(options.limit))) : LIMITS.results;
    const matches = [];
    // The budget bounds the combinatorial part (joining candidates into tuples).
    // Scanning each morpheme once per node is linear in the size of the corpus,
    // so it is not charged: otherwise a larger corpus alone would exhaust it.
    let operations = 0;
    const step = () => {
      if(++operations > LIMITS.operations) throw new QueryError("SEARCH_LIMIT", "This query is too broad. Add annotation constraints or select fewer witnesses.", null, "tooBroad");
    };
    const lowerBound = (list, value) => {
      let left = 0, right = list.length;
      while(left < right){
        const middle = (left + right) >>> 1;
        if(list[middle] < value) left = middle + 1;
        else right = middle;
      }
      return left;
    };

    for(const segment of segments){
      if(selected && !selected.has(segment.w)) continue;
      const tokens = segment.tokens;
      if(!tokens.length) continue;
      // Retain original token positions. Removing filtered POS tags first would
      // manufacture adjacency between morphemes that were never adjacent.
      const candidates = [];
      for(const node of compiled.nodes){
        const positions = [];
        tokens.forEach((token, position) => {
          if(!excluded.has(token.pos) && testNode(node, token)) positions.push(position);
        });
        if(!positions.length) break;          // no tuple can be completed in this segment
        candidates.push(positions);
      }
      if(candidates.length < compiled.nodes.length) continue;
      const path = [];
      function visit(depth, position){
        step();
        path[depth] = position;
        if(depth === compiled.nodes.length - 1){
          if(matches.length === limit) return false;
          matches.push({tokens:path.map(p => tokens[p].index)});
          return true;
        }
        const distance = compiled.distances[depth], next = candidates[depth + 1];
        const end = Math.min(tokens.length - 1, position + distance.max);
        for(let i = lowerBound(next, position + distance.min); i < next.length && next[i] <= end; i++){
          if(!visit(depth + 1, next[i])) return false;
        }
        return true;
      }
      for(const position of candidates[0]){
        if(!visit(0, position)) return {matches, truncated:true};
      }
    }
    return {matches, truncated:false};
  }

  return Object.freeze({compile, search, QueryError, LIMITS});
});
