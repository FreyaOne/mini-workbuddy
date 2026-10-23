import DefaultTheme from 'vitepress/theme'
import './custom.css'
import type { Theme } from 'vitepress'
import 'viewerjs/dist/viewer.min.css';
import imageViewer from 'vitepress-plugin-image-viewer';
import vImageViewer from 'vitepress-plugin-image-viewer/lib/vImageViewer.vue';
import { useRoute } from 'vitepress';

export default {
    extends: DefaultTheme,
    enhanceApp({ app }) {
        // 图片点击放大：正文里的架构图看不清时用得着
        app.component('vImageViewer', vImageViewer);
    },
    setup() {
        const route = useRoute();
        imageViewer(route);
    }
} satisfies Theme
