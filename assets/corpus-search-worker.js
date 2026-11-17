/* Keep user regex evaluation away from the browser's UI thread.
 *
 * Messages in:  {type:"init", segments}                       → replies {type:"ready"}
 *               {type:"search", id, query, mode, options}     → replies {id, result} or {id, error}
 * The page keeps one worker alive and reuses it; it terminates the worker only
 * to stop a search that is still running (a new query, or the time limit).
 */
"use strict";
importScripts("corpus-query.js");

let corpusSegments = null;
self.onmessage = function(event){
  const request = event.data;
  if(!request || typeof request !== "object") return;
  if(request.type === "init"){
    corpusSegments = request.segments;
    self.postMessage({type:"ready"});
    return;
  }
  if(request.type !== "search") return;
  try{
    if(!Array.isArray(corpusSegments)) throw new CorpusQuery.QueryError("NOT_READY", "The corpus has not loaded yet.");
    const compiled = CorpusQuery.compile(request.query, request.mode);
    const result = CorpusQuery.search(compiled, corpusSegments, request.options);
    self.postMessage({id:request.id, result});
  }catch(error){
    const failure = {code:error.code || "SEARCH_ERROR", message:error.message || "Search failed."};
    if(error.detail != null) failure.detail = error.detail;
    if(error.position != null) failure.position = error.position;
    if(error.reason != null) failure.reason = error.reason;
    self.postMessage({id:request.id, error:failure});
  }
};
