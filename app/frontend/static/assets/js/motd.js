var obfuscators = [];
var styleMap = {
    '§0': 'color:#000000',
    '§1': 'color:#0000AA',
    '§2': 'color:#00AA00',
    '§3': 'color:#00AAAA',
    '§4': 'color:#AA0000',
    '§5': 'color:#AA00AA',
    '§6': 'color:#FFAA00',
    '§7': 'color:#AAAAAA',
    '§8': 'color:#555555',
    '§9': 'color:#5555FF',
    '§a': 'color:#55FF55',
    '§b': 'color:#55FFFF',
    '§c': 'color:#FF5555',
    '§d': 'color:#FF55FF',
    '§e': 'color:#FFFF55',
    '§f': 'color:var(--white)',
    '§l': 'font-weight:bold',
    '§m': 'text-decoration:line-through',
    '§n': 'text-decoration:underline',
    '§o': 'font-style:italic',
};
function obfuscate(string, elem) {
    var magicSpan;
    if (string.indexOf('<br>') > -1) {
        elem.innerHTML = string;
        elem.childNodes.array.forEach(currNode => {
            if (currNode.nodeType === 3) {
                magicSpan = document.createElement('span');
                magicSpan.innerHTML = currNode.nodeValue;
                elem.replaceChild(magicSpan, currNode);
                init(magicSpan);
            }
        });
    } else {
        init(elem, string);
    }
    function init(el, str) {
        var i = 0,
            obsStr = str || el.innerHTML,
            len = obsStr.length;
        obfuscators.push(window.setInterval(function () {
            if (i >= len) i = 0;
            obsStr = replaceRand(obsStr, i);
            el.innerHTML = obsStr;
            i++;
        }, 0));
    }
    function randInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }
    function replaceRand(string, i) {
        var randChar = String.fromCharCode(randInt(64, 95));
        return string.substr(0, i) + randChar + string.substr(i + 1, string.length);
    }
}
function applyCode(string, codes) {
    var elem = document.createElement('span'),
        obfuscated = false;
    codes.forEach(code => {
        elem.style.cssText += styleMap[code] + ';';
        if (code === '§k') {
            obfuscate(string, elem);
            obfuscated = true;
        }
    });
    if (!obfuscated) elem.innerHTML = string;
    return elem;
}
function parseStyle(string) {
    var final = document.createDocumentFragment();
    console.log("STRING : " + string)
    string = string.replace(/\n|\\n/g, '<br>');
    string = string.split('§r');
    string.forEach(item => {
        var apply = [];
        if (item.length > 0) {
            apply = item.match(/§.{1}/g) || [];
            apply.forEach(code => {
                item = item.replace(code, '')
            });
            final.appendChild(applyCode(item, apply));
        }
    });
    return final;
}
function clearObfuscators() {
    obfuscators.slice().reverse().forEach(item => {
        clearInterval(item);
    });
    obfuscators = [];
}
function initParser(input, output) {
    clearObfuscators();
    var input = document.getElementById(input),
        output = document.getElementById(output);
    if (input != null && output != null) {
        var parsed = parseStyle(input.innerHTML);
        output.innerHTML = '';
        output.appendChild(parsed);
    }
}
