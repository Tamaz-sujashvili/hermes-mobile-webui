(function(){
  const EVENT_ATTRS = {
    click: 'data-ui-click',
    input: 'data-ui-input',
    change: 'data-ui-change',
    submit: 'data-ui-submit',
    keydown: 'data-ui-keydown',
    dragstart: 'data-ui-dragstart',
    dragend: 'data-ui-dragend',
    dragenter: 'data-ui-dragenter',
    dragleave: 'data-ui-dragleave',
    dragover: 'data-ui-dragover',
    drop: 'data-ui-drop',
    blur: 'data-ui-blur',
  };

  function _isSpace(ch){
    return ch === ' ' || ch === '\n' || ch === '\t' || ch === '\r';
  }

  function _findMatching(text, start, openChar, closeChar){
    let depth = 0;
    let quote = null;
    for(let i = start; i < text.length; i++){
      const ch = text[i];
      if(quote){
        if(ch === '\\'){ i += 1; continue; }
        if(ch === quote) quote = null;
        continue;
      }
      if(ch === '"' || ch === "'"){
        quote = ch;
        continue;
      }
      if(ch === openChar) depth += 1;
      else if(ch === closeChar){
        depth -= 1;
        if(depth === 0) return i;
      }
    }
    return -1;
  }

  function _scanTopLevel(text, onToken){
    let quote = null;
    let paren = 0;
    let brace = 0;
    let bracket = 0;
    for(let i = 0; i < text.length; i++){
      const ch = text[i];
      if(quote){
        if(ch === '\\'){ i += 1; continue; }
        if(ch === quote) quote = null;
        continue;
      }
      if(ch === '"' || ch === "'"){
        quote = ch;
        continue;
      }
      if(ch === '(') paren += 1;
      else if(ch === ')') paren -= 1;
      else if(ch === '{') brace += 1;
      else if(ch === '}') brace -= 1;
      else if(ch === '[') bracket += 1;
      else if(ch === ']') bracket -= 1;
      if(paren || brace || bracket) continue;
      if(onToken(i, ch) === true) return i;
    }
    return -1;
  }

  function _splitTopLevel(text, delimiter){
    const parts = [];
    let start = 0;
    _scanTopLevel(text, (i, ch) => {
      if(ch === delimiter){
        const part = text.slice(start, i).trim();
        if(part) parts.push(part);
        start = i + 1;
      }
      return false;
    });
    const tail = text.slice(start).trim();
    if(tail) parts.push(tail);
    return parts;
  }

  function _findTopLevelToken(text, token){
    return _scanTopLevel(text, (i) => text.startsWith(token, i));
  }

  function _findLastTopLevelDot(text){
    let last = -1;
    _scanTopLevel(text, (i, ch) => {
      if(ch === '.') last = i;
      return false;
    });
    return last;
  }

  function _findAssignmentIndex(text){
    return _scanTopLevel(text, (i, ch) => {
      if(ch !== '=') return false;
      const prev = text[i - 1] || '';
      const next = text[i + 1] || '';
      if(prev === '=' || prev === '!' || prev === '<' || prev === '>' || next === '=' || prev === '>'){
        return false;
      }
      return true;
    });
  }

  function _stripOuterParens(text){
    let value = String(text || '').trim();
    while(value.startsWith('(') && value.endsWith(')')){
      const close = _findMatching(value, 0, '(', ')');
      if(close !== value.length - 1) break;
      value = value.slice(1, -1).trim();
    }
    return value;
  }

  function _unquote(text){
    const raw = String(text || '').trim();
    if(raw.length < 2) return raw;
    const quote = raw[0];
    if((quote !== '"' && quote !== "'") || raw[raw.length - 1] !== quote) return raw;
    const body = raw.slice(1, -1);
    if(quote === '"'){
      try{
        return JSON.parse(raw);
      }catch(_){
        return body.replace(/\\"/g, '"').replace(/\\\\/g, '\\');
      }
    }
    return body
      .replace(/\\'/g, "'")
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '\\')
      .replace(/\\n/g, '\n')
      .replace(/\\r/g, '\r')
      .replace(/\\t/g, '\t');
  }

  function _resolveIdentifier(name, env){
    if(Object.prototype.hasOwnProperty.call(env, name)) return env[name];
    return window[name];
  }

  function _parseArgs(argText, env){
    const raw = String(argText || '').trim();
    if(!raw) return [];
    return _splitTopLevel(raw, ',').map(part => _evalExpr(part, env));
  }

  function _evalChain(expr, env){
    const text = _stripOuterParens(expr);
    let idx = 0;
    while(idx < text.length && _isSpace(text[idx])) idx += 1;
    const ident = text.slice(idx).match(/^[A-Za-z_$][\w$]*/);
    if(!ident) throw new Error(`Unsupported inline action expression: ${expr}`);
    idx += ident[0].length;
    let current = _resolveIdentifier(ident[0], env);
    let owner = null;
    while(idx < text.length){
      while(idx < text.length && _isSpace(text[idx])) idx += 1;
      const ch = text[idx];
      if(ch === '.'){
        idx += 1;
        const propMatch = text.slice(idx).match(/^[A-Za-z_$][\w$]*/);
        if(!propMatch) throw new Error(`Invalid property access in inline action: ${expr}`);
        owner = current;
        current = current?.[propMatch[0]];
        idx += propMatch[0].length;
        continue;
      }
      if(ch === '('){
        const end = _findMatching(text, idx, '(', ')');
        if(end === -1) throw new Error(`Unclosed call in inline action: ${expr}`);
        const args = _parseArgs(text.slice(idx + 1, end), env);
        if(typeof current !== 'function'){
          throw new Error(`Inline action target is not callable: ${expr}`);
        }
        current = current.apply(owner || window, args);
        owner = current;
        idx = end + 1;
        continue;
      }
      break;
    }
    return current;
  }

  function _resolveAssignmentTarget(expr, env){
    const text = _stripOuterParens(expr);
    const dot = _findLastTopLevelDot(text);
    if(dot === -1){
      return {
        set(value){
          env[text] = value;
        },
      };
    }
    const ownerExpr = text.slice(0, dot);
    const prop = text.slice(dot + 1).trim();
    const owner = _evalExpr(ownerExpr, env);
    return {
      set(value){
        owner[prop] = value;
      },
    };
  }

  function _evalObjectLiteral(text, env){
    const inner = text.slice(1, -1).trim();
    if(!inner) return {};
    const out = {};
    _splitTopLevel(inner, ',').forEach(part => {
      const idx = _scanTopLevel(part, (i, ch) => ch === ':');
      if(idx === -1){
        throw new Error(`Invalid object literal in inline action: ${text}`);
      }
      const keyRaw = part.slice(0, idx).trim();
      const valRaw = part.slice(idx + 1).trim();
      const key = /^[A-Za-z_$][\w$]*$/.test(keyRaw) ? keyRaw : _unquote(keyRaw);
      out[key] = _evalExpr(valRaw, env);
    });
    return out;
  }

  function _evalTernary(text, env){
    const qIdx = _findTopLevelToken(text, '?');
    if(qIdx === -1) return null;
    let depth = 0;
    let quote = null;
    for(let i = qIdx + 1; i < text.length; i++){
      const ch = text[i];
      if(quote){
        if(ch === '\\'){ i += 1; continue; }
        if(ch === quote) quote = null;
        continue;
      }
      if(ch === '"' || ch === "'"){
        quote = ch;
        continue;
      }
      if(ch === '(' || ch === '{' || ch === '[') depth += 1;
      else if(ch === ')' || ch === '}' || ch === ']') depth -= 1;
      else if(depth === 0 && ch === '?') depth += 1;
      else if(depth > 0 && ch === ':') depth -= 1;
      else if(depth === 0 && ch === ':'){
        return _evalExpr(text.slice(0, qIdx), env)
          ? _evalExpr(text.slice(qIdx + 1, i), env)
          : _evalExpr(text.slice(i + 1), env);
      }
    }
    return null;
  }

  function _evalExpr(expr, env){
    const text = _stripOuterParens(expr);
    if(!text) return undefined;

    const ternary = _evalTernary(text, env);
    if(ternary !== null) return ternary;

    const orIdx = _findTopLevelToken(text, '||');
    if(orIdx !== -1){
      return _evalExpr(text.slice(0, orIdx), env) || _evalExpr(text.slice(orIdx + 2), env);
    }
    const andIdx = _findTopLevelToken(text, '&&');
    if(andIdx !== -1){
      return _evalExpr(text.slice(0, andIdx), env) && _evalExpr(text.slice(andIdx + 2), env);
    }
    for(const op of ['===', '!==', '==', '!=']){
      const idx = _findTopLevelToken(text, op);
      if(idx !== -1){
        const left = _evalExpr(text.slice(0, idx), env);
        const right = _evalExpr(text.slice(idx + op.length), env);
        if(op === '===') return left === right;
        if(op === '!==') return left !== right;
        if(op === '==') return left == right; // eslint-disable-line eqeqeq
        return left != right; // eslint-disable-line eqeqeq
      }
    }

    if((text.startsWith('"') && text.endsWith('"')) || (text.startsWith("'") && text.endsWith("'"))){
      return _unquote(text);
    }
    if(text === 'true') return true;
    if(text === 'false') return false;
    if(text === 'null') return null;
    if(text === 'undefined') return undefined;
    if(/^-?\d+(?:\.\d+)?$/.test(text)) return Number(text);
    if(text.startsWith('{') && text.endsWith('}')) return _evalObjectLiteral(text, env);

    return _evalChain(text, env);
  }

  function _evalStatement(statement, env){
    const text = String(statement || '').trim();
    if(!text) return;
    if(text.startsWith('return ')){
      return _evalStatement(text.slice(7), env);
    }
    if(text.startsWith('if(')){
      const condEnd = _findMatching(text, 2, '(', ')');
      if(condEnd === -1) throw new Error(`Malformed inline if statement: ${text}`);
      const condition = text.slice(3, condEnd);
      const body = text.slice(condEnd + 1).trim();
      if(_evalExpr(condition, env)){
        if(body.startsWith('{') && body.endsWith('}')){
          return _runInlineStatements(body.slice(1, -1), env);
        }
        return _evalStatement(body, env);
      }
      return;
    }
    const declMatch = text.match(/^(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(.+)$/);
    if(declMatch){
      env[declMatch[1]] = _evalExpr(declMatch[2], env);
      return env[declMatch[1]];
    }
    const assignIdx = _findAssignmentIndex(text);
    if(assignIdx !== -1){
      const target = _resolveAssignmentTarget(text.slice(0, assignIdx), env);
      const value = _evalExpr(text.slice(assignIdx + 1), env);
      target.set(value);
      return value;
    }
    return _evalExpr(text, env);
  }

  function _runInlineStatements(code, env){
    let result;
    _splitTopLevel(String(code || ''), ';').forEach(part => {
      result = _evalStatement(part, env);
    });
    return result;
  }

  function _dispatchAction(eventName, event, element){
    const attrName = EVENT_ATTRS[eventName];
    if(!attrName) return;
    const code = element.getAttribute(attrName);
    if(!code) return;
    const wrappedEvent = Object.create(event);
    wrappedEvent.currentTarget = element;
    wrappedEvent.target = event.target;
    wrappedEvent.preventDefault = event.preventDefault ? event.preventDefault.bind(event) : function(){};
    wrappedEvent.stopPropagation = event.stopPropagation ? event.stopPropagation.bind(event) : function(){};
    const env = {
      event: wrappedEvent,
      this: element,
      window,
      document,
      S: window.S,
      ONBOARDING: window.ONBOARDING,
    };
    return _runInlineStatements(code, env);
  }

  function _bindDelegated(eventName, options){
    const attrName = EVENT_ATTRS[eventName];
    if(!attrName) return;
    const domEvent = eventName === 'blur' ? 'focusout' : eventName;
    document.addEventListener(domEvent, (event) => {
      const target = event.target && event.target.closest ? event.target.closest(`[${attrName}]`) : null;
      if(!target) return;
      _dispatchAction(eventName, event, target);
    }, options || false);
  }

  [
    'click',
    'input',
    'change',
    'submit',
    'keydown',
    'dragstart',
    'dragend',
    'dragenter',
    'dragleave',
    'dragover',
    'drop',
  ].forEach(name => {
    const useCapture = name === 'submit'
      || name === 'click'
      || name === 'keydown'
      || name.startsWith('drag');
    _bindDelegated(name, useCapture);
  });
  _bindDelegated('blur', true);
})();
