import {
  ComponentProps,
  useBlockNoteEditor,
  useComponentsContext,
  useSelectedBlocks,
} from '@blocknote/react';
import { Loader } from '@openfun/cunningham-react';
import { ReactNode, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { Box, Text } from '@/components';

import { AIActions, useAI } from '../api/useAI';

export function AIGroupButton() {
  const editor = useBlockNoteEditor();
  const Components = useComponentsContext();
  const selectedBlocks = useSelectedBlocks(editor);
  const { t } = useTranslation();

  const show = useMemo(() => {
    return !!selectedBlocks.find((block) => block.content !== undefined);
  }, [selectedBlocks]);

  if (!show || !editor.isEditable || !Components) {
    return null;
  }

  return (
    <Components.Generic.Menu.Root>
      <Components.Generic.Menu.Trigger>
        <Components.FormattingToolbar.Button
          className="bn-button bn-menu-item"
          data-test="ai-actions"
          label="AI"
          mainTooltip={t('AI Actions')}
          icon={
            <Text $isMaterialIcon $size="l">
              auto_awesome
            </Text>
          }
        />
      </Components.Generic.Menu.Trigger>
      <Components.Generic.Menu.Dropdown
        className="bn-menu-dropdown bn-drag-handle-menu"
        sub={true}
      >
        <AIMenuItem
          action="prompt"
          icon={
            <Text $isMaterialIcon $size="s">
              text_fields
            </Text>
          }
        >
          {t('Use as prompt')}
        </AIMenuItem>
        <AIMenuItem
          action="rephrase"
          icon={
            <Text $isMaterialIcon $size="s">
              refresh
            </Text>
          }
        >
          {t('Rephrase')}
        </AIMenuItem>
        <AIMenuItem
          action="summarize"
          icon={
            <Text $isMaterialIcon $size="s">
              summarize
            </Text>
          }
        >
          {t('Summarize')}
        </AIMenuItem>
        <AIMenuItem
          action="correct"
          icon={
            <Text $isMaterialIcon $size="s">
              check
            </Text>
          }
        >
          {t('Correct')}
        </AIMenuItem>
        <Components.Generic.Menu.Root position="right" sub={true}>
          <Components.Generic.Menu.Trigger sub={false}>
            <Components.Generic.Menu.Item
              className="bn-menu-item"
              subTrigger={true}
            >
              <Box $direction="row" $gap="0.6rem">
                <Text $isMaterialIcon $size="s">
                  translate
                </Text>
                {t('Language')}
              </Box>
            </Components.Generic.Menu.Item>
          </Components.Generic.Menu.Trigger>
          <Components.Generic.Menu.Dropdown
            sub={false}
            className="bn-menu-dropdown bn-drag-handle-menu"
          >
            <AIMenuItem action="translate_en">{t('English')}</AIMenuItem>
            <AIMenuItem action="translate_fr">{t('French')}</AIMenuItem>
            <AIMenuItem action="translate_de">{t('German')}</AIMenuItem>
          </Components.Generic.Menu.Dropdown>
        </Components.Generic.Menu.Root>
      </Components.Generic.Menu.Dropdown>
    </Components.Generic.Menu.Root>
  );
}

/**
 * Item is derived from Mantime, some props seem lacking or incorrect.
 */
type ItemDefault = ComponentProps['Generic']['Menu']['Item'];
type ItemProps = Omit<ItemDefault, 'onClick'> & {
  rightSection?: ReactNode;
  closeMenuOnClick?: boolean;
  onClick: (e: React.MouseEvent) => void;
};

interface AIMenuItemProps {
  action: AIActions;
  children: ReactNode;
  icon?: ReactNode;
}

const AIMenuItem = ({ action, children, icon }: AIMenuItemProps) => {
  const editor = useBlockNoteEditor();
  const Components = useComponentsContext();
  const { mutateAsync: requestAI, isPending } = useAI();

  const handleAIAction = useCallback(async () => {
    const selectedBlocks = editor.getSelection()?.blocks;

    if (!selectedBlocks || selectedBlocks.length === 0) {
      return;
    }

    const markdown = await editor.blocksToMarkdownLossy(selectedBlocks);
    const responseAI = await requestAI({
      text: markdown,
      action,
    });

    if (!responseAI.answer) {
      return;
    }

    const blockMarkdown = await editor.tryParseMarkdownToBlocks(
      responseAI.answer,
    );
    editor.replaceBlocks(selectedBlocks, blockMarkdown);
  }, [editor, requestAI, action]);

  if (!Components) {
    return null;
  }

  const Item = Components.Generic.Menu.Item as React.FC<ItemProps>;

  return (
    <Item
      closeMenuOnClick={false}
      icon={icon}
      onClick={(e: React.MouseEvent) => {
        e.stopPropagation();
        void handleAIAction();
      }}
      rightSection={isPending ? <Loader size="small" /> : undefined}
    >
      {children}
    </Item>
  );
};
