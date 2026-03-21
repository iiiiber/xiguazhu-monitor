/**
 * 西瓜猪开放平台 API 签名工具
 * 签名算法: MD5(appSecret + 参数按key字母排序拼接 + appSecret).toLowerCase()
 */

const crypto = require('crypto');

/**
 * 生成API签名
 * @param {Object} params - 请求参数（不包含sign字段）
 * @param {string} appSecret - 应用密钥
 * @returns {string} 签名字符串
 */
function generateSign(params, appSecret) {
  // 1. 复制参数并移除sign字段
  const filteredParams = { ...params };
  delete filteredParams.sign;

  // 2. 过滤空值并按key排序
  const sortedKeys = Object.keys(filteredParams)
    .filter(key => {
      const value = filteredParams[key];
      return value !== null && value !== undefined && value !== '';
    })
    .sort();

  // 3. 拼接参数字符串
  let paramStr = '';
  for (const key of sortedKeys) {
    const value = filteredParams[key];
    // 处理布尔类型
    if (typeof value === 'boolean') {
      paramStr += key + (value ? 'true' : 'false');
    } else {
      paramStr += key + value;
    }
  }

  // 4. 前后加上appSecret，MD5加密并转小写
  const signStr = appSecret + paramStr + appSecret;
  return crypto.createHash('md5').update(signStr, 'utf8').digest('hex').toLowerCase();
}

/**
 * 构建带签名的请求参数
 * @param {Object} params - 业务参数
 * @param {string} appSecret - 应用密钥
 * @returns {Object} 包含timestamp和sign的完整参数
 */
function buildSignedParams(params, appSecret) {
  const timestamp = Math.floor(Date.now() / 1000);
  const allParams = {
    ...params,
    timestamp
  };
  
  const sign = generateSign(allParams, appSecret);
  return {
    ...allParams,
    sign
  };
}

module.exports = {
  generateSign,
  buildSignedParams
};
