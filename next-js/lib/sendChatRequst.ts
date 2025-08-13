export async function sendChatRequest(newMessages, setMessages, setIsLoading){
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages,
          first_message: newMessages.length === 1,
          attachment_ids: [],
        }),
      })

      if (!response.ok || !response.body) {
        const errorText = await response.text()
        throw new Error(`Server error: ${errorText || response.statusText}`)
      }
      
      const assistantMessageId = `assistant-${Date.now()}`
      setMessages((prev) => [
        ...prev,
        { id: assistantMessageId, role: 'assistant', content: '' },
      ])

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let responseText = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        responseText += decoder.decode(value)
      }

      let newContent = responseText
      try {
        const parsed = JSON.parse(responseText)
        if(parsed.answer){
          newContent = parsed.answer
        }
      } catch(e) {
        // ?
      }
        // const chunk = decoder.decode(value)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              // ? { ...msg, content: msg.content + chunk }
              ? { ...msg, content: newContent }
              : msg
          )
        )
    } catch (error) {
      console.error('An error occurred during the request:', error)
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: '죄송합니다, 답변을 생성하는 중 오류가 발생했습니다.',
        },
      ])
    } finally {
      setIsLoading(false)
    }
}