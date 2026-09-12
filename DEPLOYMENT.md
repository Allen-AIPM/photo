# GitHub 与 Cloudflare 部署说明

这是可独立构建的 React + Vite 静态网站。网站内容、18 张原图、压缩图片、五种动效源码、构建脚本、依赖锁文件都在项目内，不依赖桌面原始灵感库目录，也不需要 API Key 或数据库。

## 1. 上传 GitHub

建议将 **lgk 文件夹里面的内容**作为仓库根目录，根目录能直接看到 `package.json`。

应提交 `src/`、`public/`、`scripts/`、`.github/`、`index.html`、`vite.config.js`、`package.json`、`package-lock.json`、`.node-version`、`.nvmrc`、`.gitignore`、`wrangler.jsonc` 和说明文档。保留 `public/image` 中的原图，否则原图下载会失效。

`node_modules/`、`dist/`、`.wrangler/` 和本地环境文件已列入 `.gitignore`。交付文件夹包含 `dist/` 以便直接使用构建产物；通过 Git 提交时会自动忽略。若使用 GitHub 网页手动上传，不要选中 `dist/` 或 `node_modules/`，网页上传不会替你应用本地忽略规则。

附带 GitHub Actions，在仓库根目录执行 `npm ci`、`npm run build`、`npm run check`。它只检查构建，不会自动发布，也不需要配置密钥。

## 2. 推荐：Cloudflare Pages 连接 GitHub

在 Cloudflare 的 Workers & Pages 中创建 Pages 项目，导入 GitHub 仓库：

| 设置 | 值 |
|---|---|
| 项目根目录 | 仓库根目录；若把整个 lgk 文件夹放入仓库则填 `lgk` |
| 构建命令 | `npm run build` |
| 构建输出目录 | `dist` |
| Node.js | `22.16.0`；项目附带 `.node-version` 与 `.nvmrc` |
| 环境变量 | 网站运行无需密钥；如需显式指定 Node，可设置 `NODE_VERSION=22.16.0` |

默认安装步骤会安装依赖。若自定义安装命令，使用 `npm ci`，不要使用 `--omit=dev`，构建需要 Vite 与 Sharp。

`npm run build` 会先检查/生成 WebP 变体和尺寸清单，再输出 `dist`。前端路由使用首页锚点，不需要额外服务端接口。

Cloudflare Pages 的配置依据：[React 部署指南](https://developers.cloudflare.com/pages/framework-guides/deploy-a-react-site/)、[Vite 构建配置](https://developers.cloudflare.com/pages/framework-guides/deploy-a-vite3-project/)。

## 3. 如果选择 Cloudflare Workers 的 GitHub 构建

项目也附带 `wrangler.jsonc`，声明 `dist` 静态资源及单页应用回退，无需 Worker 服务端代码。

| 设置 | 值 |
|---|---|
| 根目录 | 同上 |
| 构建命令 | `npm run build` |
| 部署命令 | `npx wrangler deploy` |
| Worker 名称 | 与 `wrangler.jsonc` 中的 `lgk-inspiration-library` 一致；需要改名时同时修改两处 |

已执行 `wrangler deploy --dry-run` 验证配置。预检不代表已上线，首次真实部署仍由你在 Cloudflare 完成账号授权。

依据：[Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/)、[SPA 配置](https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/)。

两种平台选一种即可；Pages 使用控制台的输出目录配置，Workers 使用 `wrangler.jsonc`。若后续启用 Workers 非生产分支预览，可按控制台要求使用 `npx wrangler versions upload`。

## 4. 本地验证

```sh
npm ci
npm run build
npm run check
npm run preview
```

打开最后显示的本地地址。开发和修改使用 `npm run dev`，也可以双击 `启动预览.cmd`。请通过本地服务器预览，不要直接双击 `dist/index.html`。

## 5. 缓存与数据边界

- `public/_headers` 给带内容哈希的脚本和 WebP 设置一年缓存，修改内容会生成新文件名；原图使用重新验证缓存。依据：[Cloudflare Headers](https://developers.cloudflare.com/pages/configuration/headers/)。
- 评论和收藏仍只保存在各自浏览器中，上传网站不会上传你本机的评论或收藏。更换域名或浏览器不会自动迁移，也不是多人共享评论系统。
- 素材数据来自 `src/data.json`。原始 Excel 不会自动同步；修改数据或图片后重新构建并提交即可。
- 后续若改为 GitHub Pages 的 `/仓库名/` 子路径托管，需要另外配置 Vite base 和资源路径。当前配置面向 Cloudflare 域名根路径，GitHub 在这里用于托管源码。
