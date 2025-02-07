/***************************************
 * 攻撃度スコアリング & 前後単語チェックサンプル
 ****************************************/

const dictionary = {
  insults: [
    "バカ", "クズ", "アホ", "ゴミ", "しね", "低能"
    // ... 必要な単語を追加
  ],
  defamation: [
    "犯罪者", "不倫している"
  ],
  harassment: [
    "お前を追い出してやる", "消え失せろ"
  ],
  threats: [
    "お前を殺す", "お前を殴りつけるぞ"
  ],
  ambiguous: [
    "頭が高いね", "よくそれでやっていけてるね"
  ]
};

function tokenize(text) {
  return text.replace(/[.,\/#!?$%\^&\*;:{}=\-_`~()]/g, " ")
             .split(/\s+/)
             .filter(Boolean);
}

function matchDictionary(token, dictArray) {
  const lowerToken = token.toLowerCase();
  for (const phrase of dictArray) {
    const lowerPhrase = phrase.toLowerCase();
    if (lowerToken.includes(lowerPhrase) || lowerPhrase.includes(lowerToken)) {
      return true;
    }
  }
  return false;
}

function analyzeText(text, dictionary) {
  const tokens = tokenize(text);
  let score = 0;
  const weights = {
    insults: 2,
    defamation: 3,
    harassment: 4,
    threats: 5,
    ambiguous: 1
  };
  const contextRange = 2;

  for (let i = 0; i < tokens.length; i++) {
    const currentToken = tokens[i];
    const leftContext = tokens.slice(Math.max(0, i - contextRange), i).join(" ");
    const rightContext = tokens.slice(i + 1, i + 1 + contextRange).join(" ");
    const contextText = leftContext + " " + currentToken + " " + rightContext;
    
    for (const [catName, dictArray] of Object.entries(dictionary)) {
      if (matchDictionary(currentToken, dictArray)) {
        score += weights[catName] || 1;
        if (/死ね|殺す|殺|潰す/.test(contextText)) {
          score += 2;
        }
      }
    }
  }
  return score;
}

function classifyScore(score) {
  if (score >= 20) {
    return "【一致】 この文章は名誉毀損や誹謗中傷に該当する可能性が非常に高いです。";
  } else if (score >= 10) {
    return "【部分一致】 一部の表現が問題となる可能性があります。";
  } else if (score > 0) {
    return "【文脈解析】 攻撃的表現を含むかもしれません。注意が必要です。";
  } else {
    return "問題なし";
  }
}

console.log("テスト実行：");
const userInput = "お前なんて要らない。さっさと消えろ。";
const totalScore = analyzeText(userInput, dictionary);
const resultMessage = classifyScore(totalScore);
console.log("スコア:", totalScore);
console.log("判定結果:", resultMessage);
