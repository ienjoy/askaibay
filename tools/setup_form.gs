/**
 * 一键创建「房东投稿」表单和配套表格。
 *
 * 用法：
 *   1. 打开 https://script.google.com → 新建项目
 *   2. 把这个文件的全部内容粘贴进去，覆盖原有的 myFunction
 *   3. 点上方 ▶ 运行（第一次会要求授权，选你的 Google 账号 → 高级 → 继续）
 *   4. 运行完在下方「执行日志」里会打印表单地址和表格地址
 *
 * 建完之后还需要手动做一步（Apps Script 没有对应接口）：
 *   打开表格 → 文件 → 共享 → 发布到网络 → 选「上线」这张表 + CSV 格式 → 发布
 */
function setup() {
  var FORM_TITLE = '湾区租房地图 · 免费发布房源';
  var FORM_DESC =
      '免费发布，无需注册。提交后我们会看一眼，通过后显示在 askaibay.com 的地图上。\n\n' +
      '请注意：你填写的全部内容——包括联系方式——都会公开显示在地图上，任何人都能看到。' +
      '请只填你愿意公开的信息。\n' +
      '房源出租后请告诉我们下架，超过 60 天会自动下架。';

  var form = FormApp.create(FORM_TITLE);
  form.setDescription(FORM_DESC);
  form.setCollectEmail(false);          // 不收邮箱：表格要公开，收了会一起公开
  form.setLimitOneResponsePerUser(false);

  form.addTextItem().setTitle('房源标题').setRequired(true)
      .setHelpText('一句话说清楚，例：Fremont 主卧带独卫，近 Ohlone College');

  form.addTextItem().setTitle('每月租金')
      .setHelpText('填数字就行，例：1800。面议就留空');

  form.addTextItem().setTitle('城市/地区').setRequired(true)
      .setHelpText('中英文都可以，例：Fremont、屋仑、San Jose');

  form.addTextItem().setTitle('邮编')
      .setHelpText('填了地图上的位置会更准。不填就只能定位到城市中心');

  form.addMultipleChoiceItem().setTitle('出租类型')
      .setChoiceValues(['整租', '单间', '合租']);

  form.addTextItem().setTitle('联系方式').setRequired(true)
      .setHelpText('⚠️ 这一项会公开显示在地图上，任何人都能看到。' +
                   '建议填微信号；不想公开手机号就不要填手机号。');

  form.addParagraphTextItem().setTitle('房源说明')
      .setHelpText('位置、交通、家具、入住要求等。地图上只显示前 120 字');

  form.addTextItem().setTitle('详情链接')
      .setHelpText('有原帖、相册或看房链接就填，没有可以不填');

  form.addMultipleChoiceItem()
      .setTitle('我确认以上信息（含联系方式）可以公开显示在地图上')
      .setChoiceValues(['我确认']).setRequired(true);

  // 建回复表格并挂上
  var ss = SpreadsheetApp.create('湾区租房地图 · 房源投稿');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  SpreadsheetApp.flush();
  ss = SpreadsheetApp.openById(ss.getId());   // 重新打开才能看到新建的回复表

  // 找出表单回复表（名字随账号语言不同，可能叫「表单回复 1」或 Form Responses 1）
  var resp = null, sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    var h = sheets[i].getRange(1, 1).getValue();
    if (String(h).indexOf('时间戳') === 0 || String(h).indexOf('Timestamp') === 0) resp = sheets[i];
  }
  if (!resp) resp = sheets[0];

  // 最右边加一列「审核」
  var lastCol = resp.getLastColumn();
  var okCol = lastCol + 1;
  resp.getRange(1, okCol).setValue('审核').setFontWeight('bold');
  resp.getRange(1, 1, 1, okCol).setBackground('#f1f3f4');
  resp.setFrozenRows(1);

  // 再建一张「上线」表，只拉审核通过的行，只把这张公开出去
  var okLetter = columnLetter(okCol);
  var lastLetter = columnLetter(okCol);
  var name = resp.getName();
  var live = ss.insertSheet('上线');
  live.getRange('A1').setFormula(
      '=IFERROR(QUERY(\'' + name + '\'!A:' + lastLetter +
      ', "select * where ' + okLetter + ' = \'是\'", 1), ' +
      'QUERY(\'' + name + '\'!A:' + lastLetter + ', "select * limit 0", 1))');

  // 用法备忘写在旁边，免得过几个月自己忘了
  live.getRange('A3').setValue('');
  var note = ss.insertSheet('说明');
  note.getRange('A1').setValue('怎么用');
  note.getRange('A2').setValue('1. 有人投稿后，在「' + name + '」表最右边的「审核」列填 是');
  note.getRange('A3').setValue('2. 「上线」表会自动只保留审核通过的行');
  note.getRange('A4').setValue('3. 「上线」表已发布为 CSV，网站每次更新会来读它');
  note.getRange('A5').setValue('4. 想下架某条房源：把「审核」列的 是 删掉即可');
  note.getRange('A6').setValue('5. 只发布「上线」这一张表，不要发布整个表格');
  note.setColumnWidth(1, 520);

  // 网站上的表单要直接把数据发给 Google，需要每个问题的 entry 编号。
  // 生成一个预填链接，从里面把编号解析出来——这是唯一可靠的拿法。
  var entries = readEntryIds(form);

  Logger.log('=========== 建好了 ===========');
  Logger.log('回复表格: ' + ss.getUrl());
  Logger.log('表单编辑地址（想改问题措辞用）: ' + form.getEditUrl());
  Logger.log('');
  Logger.log('--- 把下面这段整个复制给 Claude ---');
  Logger.log("window.FORM_ACTION = '" +
             form.getPublishedUrl().replace(/\/viewform.*$/, '/formResponse') + "';");
  Logger.log('window.FORM_ENTRIES = ' + JSON.stringify(entries, null, 2) + ';');
  Logger.log('--- 复制到这里为止 ---');
  Logger.log('');
  Logger.log('还差一步：打开上面的表格 → 文件 → 共享 → 发布到网络');
  Logger.log('  左边选「上线」，右边格式选「逗号分隔值 (.csv)」，点发布，把网址也给 Claude');
}

/** 用预填链接反查每个问题的 entry 编号 */
function readEntryIds(form) {
  var probe = {
    title: '__T__', price: '__P__', city: '__C__', zip: '__Z__',
    kind: null, contact: '__X__', note: '__N__', link: '__L__', agree: null
  };
  var order = ['title', 'price', 'city', 'zip', 'kind', 'contact', 'note', 'link', 'agree'];
  var items = form.getItems();
  var resp = form.createResponse();
  for (var i = 0; i < items.length && i < order.length; i++) {
    var key = order[i], it = items[i], type = it.getType();
    if (type === FormApp.ItemType.MULTIPLE_CHOICE) {
      var choices = it.asMultipleChoiceItem().getChoices();
      resp = resp.withItemResponse(
          it.asMultipleChoiceItem().createResponse(choices[0].getValue()));
    } else if (type === FormApp.ItemType.PARAGRAPH_TEXT) {
      resp = resp.withItemResponse(it.asParagraphTextItem().createResponse(probe[key]));
    } else {
      resp = resp.withItemResponse(it.asTextItem().createResponse(probe[key]));
    }
  }
  var url = resp.toPrefilledUrl();
  var out = {};
  var pairs = url.split('?')[1].split('&');
  var byValue = {'__T__': 'title', '__P__': 'price', '__C__': 'city', '__Z__': 'zip',
                 '__X__': 'contact', '__N__': 'note', '__L__': 'link'};
  var choiceEntries = [];
  for (var j = 0; j < pairs.length; j++) {
    var kv = pairs[j].split('=');
    if (kv[0].indexOf('entry.') !== 0) continue;
    var val = decodeURIComponent(kv[1].replace(/\+/g, ' '));
    if (byValue[val]) out[byValue[val]] = kv[0];
    else choiceEntries.push(kv[0]);          // 两个单选题：出租类型、公开确认
  }
  if (choiceEntries.length > 0) out.kind = choiceEntries[0];
  if (choiceEntries.length > 1) out.agree = choiceEntries[1];
  return out;
}

function columnLetter(n) {
  var s = '';
  while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = (n - m - 1) / 26; }
  return s;
}
