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

  Logger.log('=========== 建好了 ===========');
  Logger.log('表单填写地址（给房东）: ' + form.getPublishedUrl());
  Logger.log('表单编辑地址（你自己改问题用）: ' + form.getEditUrl());
  Logger.log('回复表格: ' + ss.getUrl());
  Logger.log('');
  Logger.log('还差一步：打开上面的表格 → 文件 → 共享 → 发布到网络');
  Logger.log('  左边选「上线」，右边格式选「逗号分隔值 (.csv)」，点发布，复制网址');
}

function columnLetter(n) {
  var s = '';
  while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = (n - m - 1) / 26; }
  return s;
}
